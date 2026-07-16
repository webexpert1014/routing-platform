from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TripPlanSerializer
from .services.hos_engine import HosPlanner, plan_result_to_dict
from .services.log_drawer import render_logs
from .services.routing_client import (
    fetch_route,
    geocode_address,
    reverse_geocode,
    suggest_addresses,
)


class GeocodeSuggestView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        if lat is not None and lng is not None:
            try:
                result = reverse_geocode(float(lat), float(lng))
            except (TypeError, ValueError) as error:
                raise ValidationError("lat and lng must be valid numbers.") from error
            return Response({"result": result}, status=status.HTTP_200_OK)
        query = request.query_params.get("q", "")
        results = suggest_addresses(query, limit=5)
        return Response({"results": results}, status=status.HTTP_200_OK)


class TripPlanView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = TripPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        current = geocode_address(data["current_location"])
        pickup = geocode_address(data["pickup_location"])
        dropoff = geocode_address(data["dropoff_location"])
        route = fetch_route([current, pickup, dropoff])
        if len(route["legs"]) < 2:
            return Response(
                {
                    "detail": "Route must include both current→pickup and pickup→dropoff legs."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        available = 70.0 - float(data["current_cycle_used"])
        plan = HosPlanner(available).build(
            coordinates=route["coordinates"],
            current=current,
            dropoff=dropoff,
            legs=route["legs"],
            pickup=pickup,
        )
        payload = plan_result_to_dict(plan)
        payload["logs"] = render_logs(payload["timeline"])
        payload["route"] = {
            "coordinates": route["coordinates"],
            "cycle_exceeded_at_mile": plan.cycle_exceeded_at_mile,
        }
        return Response(payload, status=status.HTTP_200_OK)
