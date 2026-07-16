import axios from "axios";

import type { TripPlanRequest, TripPlanResponse } from "../types/trip";

const api = axios.create({
	baseURL: import.meta.env.VITE_API_BASE_URL || "",
	headers: { "Content-Type": "application/json" },
});

export type LocationSuggestion = {
	label: string;
	lat: number;
	lng: number;
};

export const planTrip = async (payload: TripPlanRequest): Promise<TripPlanResponse> => {
	const { data } = await api.post<TripPlanResponse>("/api/trips/plan/", payload);
	return data;
};

export const readApiError = (error: unknown): string => {
	if (axios.isAxiosError(error)) {
		const detail = error.response?.data?.detail;
		if (typeof detail === "string") {
			return detail;
		}
		if (detail && typeof detail === "object") {
			return JSON.stringify(detail);
		}
		if (error.response?.data && typeof error.response.data === "object") {
			const values = Object.values(error.response.data as Record<string, unknown>);
			const first = values[0];
			if (Array.isArray(first) && typeof first[0] === "string") {
				return first[0];
			}
		}
		return error.message || "Request failed.";
	}
	if (error instanceof Error) {
		return error.message;
	}
	return "Unexpected error.";
};

export const reverseGeocode = async (lat: number, lng: number): Promise<string> => {
	const { data } = await api.get<{ result: LocationSuggestion }>("/api/trips/geocode/", { params: { lat, lng } });
	return data.result.label;
};

export const suggestLocations = async (query: string): Promise<LocationSuggestion[]> => {
	const { data } = await api.get<{ results: LocationSuggestion[] }>("/api/trips/geocode/", { params: { q: query } });
	return data.results;
};
