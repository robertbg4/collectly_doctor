import unittest
import responses
import requests
from datetime import datetime

from flask_testing import TestCase

from app import create_app
from app.utils import get_auth_header


class TestCaseBase(TestCase):
    def setUp(self) -> None:
        self.mocker = responses.mock
        self.mocker.add(responses.POST, "https://drchrono.com/o/token/", json={"access_token": "test"})
        self.mocker.add(
            responses.GET,
            "https://drchrono.com/api/offices",
            json={"results": [{"start_time": "09:00:00", "end_time": "22:00:00"}], "next": None},
        )
        self.mocker.add(
            responses.GET,
            "https://drchrono.com/api/appointments",
            json={
                "results": [
                    {
                        "last_billed_date": f"{datetime.now().date().isoformat()} 09:30",
                        "duration": "30",
                    },
                    {
                        "last_billed_date": f"{datetime.now().date().isoformat()} 15:30",
                        "duration": "120",
                    },
                ],
                "next": None,
            },
        )
        self.mocker.add(responses.POST, "https://drchrono.com/api/appointments", json={})
        self.mocker.add(responses.POST, "https://drchrono.com/api/patients", json={"id": "1"})

    def create_app(self):
        app = create_app()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app


class TestApp(TestCaseBase):
    @responses.activate
    def test_appointments(self):
        response = self.client.get("/appointments")
        self.assert200(response)

        self.mocker.remove(responses.GET, "https://drchrono.com/api/appointments")
        self.mocker.add(responses.GET, "https://drchrono.com/api/appointments", status=401)
        try:
            self.client.get("/appointments")
        except requests.exceptions.HTTPError as e:
            self.assertIn("401 Client Error", str(e))

        self.mocker.remove(responses.GET, "https://drchrono.com/api/appointments")
        self.mocker.add(responses.GET, "https://drchrono.com/api/appointments", status=403)
        try:
            self.client.get("/appointments")
        except requests.exceptions.HTTPError as e:
            self.assertIn("403 Client Error", str(e))

        self.mocker.remove(responses.GET, "https://drchrono.com/api/offices")
        self.mocker.add(
            responses.GET,
            "https://drchrono.com/api/offices",
            json={"results": [], "next": None},
        )
        response = self.client.get("/appointments")
        self.assertEqual(response.status_code, 502)

        self.mocker.remove(responses.GET, "https://drchrono.com/api/offices")
        self.mocker.add(responses.GET, "https://drchrono.com/api/offices", status=500)
        try:
            self.client.get("/appointments")
        except requests.exceptions.HTTPError as e:
            self.assertIn("500 Server Error", str(e))

    @responses.activate
    def test_form(self):
        response = self.client.get(f"/form?start={datetime.now().date().isoformat()} 08:30&duration=60")
        self.assert400(response)
        response = self.client.get(f"/form?start={datetime.now().date().isoformat()} 10:30&duration=10")
        self.assert400(response)
        response = self.client.get(f"/form?start={datetime.now().date().isoformat()} 10:30&duration=765")
        self.assert400(response)
        response = self.client.get(f"/form?start={datetime.now().date().isoformat()} 10:30&duration=360")
        self.assert400(response)
        response = self.client.get(f"/form?start={datetime.now().date().isoformat()} 10:30&duration=180")
        self.assert200(response)
        self.assertTemplateUsed("form.html")
        response = self.client.get(f"/form?start={datetime.now().date().isoformat()} 10:30&duration=bad_value")
        self.assert400(response)

        data = {
            "start_time": "10:30",
            "duration": "30 min",
            "first_name": "test_first_name",
            "last_name": "test_last_name",
            "date_of_birth": "2020-12-10",
            "email": "example@test.com",
            "phone": "+1234567890",
            "gender": "Male",
            "submit": "Create",
        }
        response = self.client.post(
            f"/form?start={datetime.now().date().isoformat()} 10:30&duration=180", data=data, follow_redirects=True
        )
        self.assert200(response)
        self.assertTemplateUsed("appointments.html")

    @responses.activate
    def test_404(self):
        response = self.client.get(f"/not_exist_page")
        self.assertEqual(response.status_code, 301)
        response = self.client.get(f"/not_exist_page", follow_redirects=True)
        self.assert200(response)
        self.assertTemplateUsed("appointments.html")

    @responses.activate
    def test_get_auth_header(self):
        result = get_auth_header()
        self.assertEqual(result, "Bearer test")

        self.mocker.remove(responses.POST, "https://drchrono.com/o/token/")
        self.mocker.add(responses.POST, "https://drchrono.com/o/token/", status=400)
        try:
            get_auth_header()
        except requests.exceptions.HTTPError as e:
            self.assertIn("400 Client Error", str(e))


if __name__ == "__main__":
    unittest.main()
