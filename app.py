from datetime import datetime, timedelta

import requests
from flask import Flask, request, redirect, render_template, abort
from flask_wtf import CSRFProtect

import config
from forms import CreatePatientForm

app = Flask(__name__)
app.config.from_object(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
csrf = CSRFProtect(app)


def get_access_token(refresh_token):
    response = requests.post(
        "https://drchrono.com/o/token/",
        data={
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": config.DRCHRONO_CLIENT_ID,
            "client_secret": config.DRCHRONO_CLIENT_SECRET,
        },
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    response.raise_for_status()


headers = {
    "Authorization": f"Bearer {get_access_token(config.DRCHRONO_REFRESH_TOKEN)}",
}


@app.route("/")
def main():
    return redirect("/appointments")


@app.route("/form", methods=["GET", "POST"])
def create_appointment():
    # TODO: find exists patients
    form = CreatePatientForm()
    print(request.form)
    start = request.args.get("start")
    duration = request.args.get("duration")
    try:
        start = datetime.fromisoformat(start)
        duration = int(duration)
    except (TypeError, ValueError):
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
        response = requests.post(
            "https://drchrono.com/api/patients", headers=headers, data=patient_data
        )
        patient = response.json()
        appointment_data = {
            "patient": patient["id"],
            "doctor": config.DOCTOR_ID,
            "scheduled_time": f"{start.date()} {result['start_time']}",
            "duration": result["duration"].split(" ")[0],
            "office": config.OFFICE_ID,
            "exam_room": config.EXAM_ROOM,
        }
        print(appointment_data)
        response = requests.post(
            "https://drchrono.com/api/appointments",
            headers=headers,
            data=appointment_data,
        )
        if response.status_code == 201:
            return redirect("/appointments")
        else:
            print(response.text)
    # TODO: check that this interval is free
    start_times = [start + timedelta(minutes=i * 15) for i in range(duration // 15)]

    return render_template(
        "form.html",
        form=form,
        start_times=start_times,
        end_time=(start + timedelta(minutes=duration)).strftime("%H:%M"),
        durations=[i for i in range(15, duration + 15, 15)],
    )


# @app.route("/patients")
# def patients():
#     patients_list = []
#     patients_url = "https://drchrono.com/api/patients"
#     while patients_url:
#         data = requests.get(patients_url, headers=headers).json()
#         patients_list.extend(data["results"])
#         patients_url = data["next"]
#     return render_template("patients.html", patients=patients_list)


@app.route("/appointments")
def appointments():
    # TODO: catch api errors
    from_date = request.args.get("from_date")
    try:
        from_date = datetime.fromisoformat(from_date)
    except (TypeError, ValueError):
        from_date = datetime.now()

    date_start = from_date if from_date > datetime.now() else datetime.now()
    dates = {(date_start + timedelta(days=i)).date(): [] for i in range(0, 7)}
    date_end = date_start + timedelta(days=6)

    response = requests.get(
        "https://drchrono.com/api/offices",
        headers=headers,
        params={"doctor": config.DOCTOR_ID},
    )
    office = response.json()["results"][0]

    appointments_list = []
    appointments_url = "https://drchrono.com/api/appointments"
    params = {
        "date_range": f"{date_start.strftime('%Y-%m-%d')}/{date_end.strftime('%Y-%m-%d')}",
    }
    while appointments_url:
        response = requests.get(appointments_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
        else:
            print(response.text)
            break
        appointments_list.extend(data["results"])
        appointments_url = data["next"]

    for appointment in appointments_list:
        billed_date = datetime.fromisoformat(appointment["last_billed_date"])
        dates[billed_date.date()].append(
            Interval(
                datetime.fromisoformat(appointment["last_billed_date"]),
                int(appointment["duration"]),
                True,
            )
        )
    for date in dates:
        dates[date].sort(key=lambda x: x.finish)
        intervals = []
        # first
        day_start_time = datetime.strptime(
            f"{date.isoformat()} {office['start_time']}", "%Y-%m-%d %H:%M:%S"
        )
        day_end_time = datetime.strptime(
            f"{date.isoformat()} {office['end_time']}", "%Y-%m-%d %H:%M:%S"
        )
        if not dates[date]:
            free_duration = day_end_time - day_start_time
            dates[date].append(
                Interval(day_start_time, int(free_duration.seconds / 60), False)
            )
            continue
        free_duration = dates[date][0].start - day_start_time
        if free_duration > timedelta(minutes=0):
            intervals.append(
                Interval(day_start_time, int(free_duration.seconds / 60), False)
            )

        for i in range(0, len(dates[date]) - 1):
            intervals.append(dates[date][i])
            free_duration = dates[date][i + 1].start - dates[date][i].finish
            if free_duration > timedelta(minutes=0):
                intervals.append(
                    Interval(
                        dates[date][i].finish, int(free_duration.seconds / 60), False
                    )
                )
        # last
        intervals.append(dates[date][-1])
        free_duration = day_end_time - dates[date][-1].finish
        if free_duration > timedelta(minutes=0):
            intervals.append(
                Interval(dates[date][-1].finish, int(free_duration.seconds / 60), False)
            )

        dates[date] = intervals
    return render_template(
        "appointments.html",
        dates=dates,
        next_week=date_end + timedelta(days=1),
        previous_week_start=date_start - timedelta(weeks=1) if from_date > datetime.now() else None,
        previous_week_end=date_start - timedelta(days=1) if from_date > datetime.now()else None,
    )


class Interval(object):
    def __init__(self, start, duration, booked):
        self.start = start
        self.finish = start + timedelta(minutes=duration)
        self.duration = duration
        self.booked = booked

    def __repr__(self):
        return f"{self.start.strftime('%H:%M')} - {self.finish.strftime('%H:%M')}"


if __name__ == "__main__":
    app.run(debug=False, port=5003)
