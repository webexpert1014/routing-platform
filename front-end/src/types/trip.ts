export type MarkerType = "break_30" | "current" | "dropoff" | "fueling" | "pickup" | "reset_10";

export type DutyStatus = "driving" | "off_duty" | "on_duty_nd" | "sleeper";

export type TripMarker = {
	cumulative_miles: number;
	day_index: number;
	label: string;
	lat: number;
	lng: number;
	location: string;
	type: MarkerType;
};

export type DutySegment = {
	compliant: boolean;
	day_index: number;
	end_minutes: number;
	label: string;
	location: string;
	remark: string;
	show_bracket: boolean;
	start_minutes: number;
	status: DutyStatus;
};

export type TripLog = {
	date_label: string;
	day_index: number;
	image_base64: string;
};

export type TripPlanResponse = {
	available_cycle_hours: number;
	cycle_exceeded_at_mile: number | null;
	cycle_exceeded: boolean;
	cycle_warning: string | null;
	logs: TripLog[];
	markers: TripMarker[];
	route: {
		coordinates: [number, number][];
		cycle_exceeded_at_mile: number | null;
	};
	summary: {
		days_count: number;
		total_drive_hours: number;
		total_miles: number;
	};
	timeline: DutySegment[];
};

export type TripPlanRequest = {
	current_cycle_used: number;
	current_location: string;
	dropoff_location: string;
	pickup_location: string;
};
