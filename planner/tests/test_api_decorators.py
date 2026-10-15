import json
from types import SimpleNamespace
from unittest.mock import Mock

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase

from planner.api.decorators import api_view_json


class ApiDecoratorTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def make_request(self, method, *, authenticated=True):
        request = self.factory.generic(method, "/api/example/")
        request.user = SimpleNamespace(
            is_authenticated=authenticated,
        )
        return request

    def test_unauthenticated_request_returns_401(self):
        view = Mock()
        decorated = api_view_json(methods=["GET"])(view)

        response = decorated(
            self.make_request("GET", authenticated=False)
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content),
            {
                "success": False,
                "message": "Log in to access this API.",
            },
        )
        view.assert_not_called()

    def test_authentication_is_checked_before_method(self):
        view = Mock()
        decorated = api_view_json(methods=["GET"])(view)

        response = decorated(
            self.make_request("POST", authenticated=False)
        )

        self.assertEqual(response.status_code, 401)
        view.assert_not_called()

    def test_unsupported_method_returns_405_and_allow_header(self):
        view = Mock()
        decorated = api_view_json(methods=["GET"])(view)

        response = decorated(self.make_request("POST"))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET")
        self.assertEqual(
            json.loads(response.content),
            {
                "success": False,
                "message": "This endpoint accepts GET requests only.",
            },
        )
        view.assert_not_called()

    def test_allowed_request_reaches_view_with_arguments(self):
        expected_response = JsonResponse(
            {"success": True, "message": "Loaded."},
        )
        view = Mock(return_value=expected_response)
        decorated = api_view_json(methods=["GET"])(view)
        request = self.make_request("GET")

        response = decorated(request, 7, example="value")

        self.assertIs(response, expected_response)
        view.assert_called_once_with(
            request,
            7,
            example="value",
        )

    def test_methods_are_normalized_and_deduplicated(self):
        view = Mock()
        decorated = api_view_json(
            methods=["get", "PATCH", "GET"],
        )(view)

        response = decorated(self.make_request("POST"))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET, PATCH")

    def test_responses_are_not_cached(self):
        view = Mock(
            return_value=JsonResponse({"success": True}),
        )
        decorated = api_view_json(methods=["GET"])(view)

        requests = [
            self.make_request("GET", authenticated=False),
            self.make_request("POST"),
            self.make_request("GET"),
        ]

        for request in requests:
            with self.subTest(
                method=request.method,
                authenticated=request.user.is_authenticated,
            ):
                response = decorated(request)

                self.assertIn(
                    "no-store",
                    response["Cache-Control"],
                )

    def test_view_metadata_is_preserved(self):
        def example_view(request):
            """Example endpoint."""
            return JsonResponse({"success": True})

        decorated = api_view_json(methods=["GET"])(example_view)

        self.assertEqual(decorated.__name__, "example_view")
        self.assertEqual(decorated.__doc__, "Example endpoint.")

    def test_empty_method_list_is_rejected(self):
        with self.assertRaises(ValueError):
            api_view_json(methods=[])