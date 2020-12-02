from datetime import datetime, timedelta

from flask import Blueprint, request, redirect, render_template, abort

import config
from app.forms import CreatePatientForm
from app.utils import DrChronoSession

drchrono = DrChronoSession()

main_blueprint = Blueprint("main", __name__, template_folder="templates")


@main_blueprint.route("/form", methods=["GET", "POST"])
def create_appointment():
    # TODO: find exists patients
    form = CreatePatientForm()
    start = request.args.get("start")
    duration = request.args.get("duration")
    try:
        start = datetime.fromisoformat(start)
        duration = int(duration)
    except (TypeError, ValueError):
        abort(400)

    check_appointment_availability(start, duration)

    start_times = [start + timedelta(minutes=i * 15) for i in range(duration // 15)]
    if not start_times:
        abort(400)

    if form.validate_on_submit():
        result = request.form.to_dict()
        patient_data = {
            "doctor": config.DOCTOR_ID,
            "date_of_birth": result["date_of_birth"],
            "email": result["email"],
            "first_name": result["first_name"],
            "last_name": result["last_name"],
            "gender": result["gender"],
            "cell_phone": result["phone"],
        }
        response = drchrono.post("https://drchrono.com/api/patients", data=patient_data)
        patient = response.json()
        appointment_data = {
            "patient": patient["id"],
            "doctor": config.DOCTOR_ID,
            "scheduled_time": f"{start.date()} {result['start_time']}",
            "duration": result["duration"].split(" ")[0],
            "office": config.OFFICE_ID,
            "exam_room": config.EXAM_ROOM,
        }
        drchrono.post("https://drchrono.com/api/appointments", data=appointment_data)
        return redirect("/appointments")

    return render_template(
        "form.html",
        form=form,
        start_times=start_times,
        end_time=(start + timedelta(minutes=duration)).strftime("%H:%M"),
        durations=[i for i in range(15, duration + 15, 15)],
    )


@main_blueprint.route("/appointments")
def appointments_table():
    from_date = request.args.get("from_date")
    try:
        from_date = datetime.fromisoformat(from_date)
    except (TypeError, ValueError):
        from_date = datetime.now()

    date_start = from_date if from_date > datetime.now() else datetime.now()
    dates = {(date_start + timedelta(days=i)).date(): [] for i in range(0, 7)}
    date_end = date_start + timedelta(days=6)

    office = get_office()

    for appointment in get_appointments(date_start, date_end):
        billed_date = datetime.fromisoformat(appointment["last_billed_date"])
        dates[billed_date.date()].append(
            Interval(
                start=billed_date, finish=billed_date + timedelta(minutes=int(appointment["duration"])), booked=True
            )
        )
    for date in dates:
        dates[date].sort(key=lambda x: x.finish)

        office_start_time = datetime.strptime(f"{date.isoformat()} {office['start_time']}", "%Y-%m-%d %H:%M:%S")
        office_end_time = datetime.strptime(f"{date.isoformat()} {office['end_time']}", "%Y-%m-%d %H:%M:%S")

        if not dates[date]:
            dates[date].append(Interval(start=office_start_time, finish=office_end_time, booked=False))
            continue

        intervals = []
        if dates[date][0].start > office_start_time:
            intervals.append(Interval(start=office_start_time, finish=dates[date][0].start, booked=False))

        for i in range(0, len(dates[date]) - 1):
            intervals.append(dates[date][i])
            if dates[date][i + 1].start > dates[date][i].finish:
                intervals.append(Interval(start=dates[date][i].finish, finish=dates[date][i + 1].start, booked=False))

        intervals.append(dates[date][-1])
        if office_end_time > dates[date][-1].finish:
            intervals.append(Interval(start=dates[date][-1].finish, finish=office_end_time, booked=False))

        dates[date] = intervals
    return render_template(
        "appointments.html",
        dates=dates,
        next_week=date_end + timedelta(days=1),
        previous_week_start=date_start - timedelta(weeks=1) if from_date > datetime.now() else None,
        previous_week_end=date_start - timedelta(days=1) if from_date > datetime.now() else None,
    )


def get_office(attempt_count=0):
    response = drchrono.get("https://drchrono.com/api/offices", params={"doctor": config.DOCTOR_ID})
    offices = response.json()["results"]
    if not offices:
        if attempt_count > config.REQUEST_ATTEMPT_LIMIT:
            abort(502)
        return get_office(attempt_count + 1)
    return offices[0]


def get_appointments(date_start, date_end):
    appointments_list = []
    appointments_url = "https://drchrono.com/api/appointments"
    params = {"date_range": f"{date_start.strftime('%Y-%m-%d')}/{date_end.strftime('%Y-%m-%d')}"}
    while appointments_url:
        data = drchrono.get(appointments_url, params=params).json()
        appointments_list.extend(data["results"])
        appointments_url = data["next"]
    return appointments_list


def check_appointment_availability(start, duration):
    current_interval = Interval(start=start, finish=start + timedelta(minutes=duration), booked=True)
    office = get_office()

    office_start_time = datetime.strptime(f"{start.date().isoformat()} {office['start_time']}", "%Y-%m-%d %H:%M:%S")
    if current_interval.start < office_start_time:
        abort(400)
    office_end_time = datetime.strptime(f"{start.date().isoformat()} {office['end_time']}", "%Y-%m-%d %H:%M:%S")
    if current_interval.finish > office_end_time:
        abort(400)

    appointments = []
    for appointment in get_appointments(date_start=start, date_end=start):
        billed_date = datetime.fromisoformat(appointment["last_billed_date"])
        appointments.append(
            Interval(
                start=billed_date, finish=billed_date + timedelta(minutes=int(appointment["duration"])), booked=True
            )
        )
    if have_intersection(appointments, current_interval):
        abort(400)


def have_intersection(intervals, current):
    for interval in intervals:
        if max(interval.start, current.start) < min(interval.finish, current.finish):
            return True
    return False


class Interval(object):
    def __init__(self, start, finish, booked):
        self.start = start
        self.finish = finish
        self.duration = (finish - start).seconds // 60
        self.booked = booked

    def __repr__(self):
        return f"{self.start.strftime('%H:%M')} - {self.finish.strftime('%H:%M')}"
