from requests import Session

import config


def get_auth_header():
    with Session() as requests:
        response = requests.post(
            "https://drchrono.com/o/token/",
            data={
                "refresh_token": config.DRCHRONO_REFRESH_TOKEN,
                "grant_type": "refresh_token",
                "client_id": config.DRCHRONO_CLIENT_ID,
                "client_secret": config.DRCHRONO_CLIENT_SECRET,
            },
        )
        if response.status_code == 200:
            return f"Bearer {response.json()['access_token']}"
        response.raise_for_status()


authorization_header = {"Authorization": ""}


class DrChronoSession(Session):
    def request(self, method, url, attempt_count=0, **kwargs):
        kwargs["headers"] = dict(authorization_header, **kwargs.get("headers", {}))
        response = super().request(method, url, **kwargs)
        if response.status_code in (200, 201):
            return response
        if attempt_count > config.REQUEST_ATTEMPT_LIMIT:
            response.raise_for_status()
        if response.status_code == 401:
            authorization_header["Authorization"] = get_auth_header()
            kwargs["headers"].pop("Authorization")
            return self.request(method, url, attempt_count=attempt_count + 1, **kwargs)
        if response.status_code == 500:
            return self.request(method, url, attempt_count=attempt_count + 1, **kwargs)
        response.raise_for_status()
