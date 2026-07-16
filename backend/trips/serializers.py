from rest_framework import serializers


class TripPlanSerializer(serializers.Serializer):
    current_cycle_used = serializers.FloatField(min_value=0, max_value=70)
    current_location = serializers.CharField(max_length=500)
    dropoff_location = serializers.CharField(max_length=500)
    pickup_location = serializers.CharField(max_length=500)
