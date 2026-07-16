import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Layer, Marker, Source, type MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import { reverseGeocode } from "../api/trips";
import type { TripMarker, TripPlanResponse } from "../types/trip";

type RouteMapProps = {
	plan: TripPlanResponse;
};

type SelectedCheckpoint = {
	index: number;
	marker: TripMarker;
};

const DETAIL_ZOOM = 10;
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const ROUTE_STOP_TYPES = new Set<TripMarker["type"]>(["break_30", "fueling", "reset_10"]);

const MARKER_COLORS: Record<TripMarker["type"], string> = {
	break_30: "#ffac5a",
	current: "#b9c8de",
	dropoff: "#ffb4ab",
	fueling: "#57f1db",
	pickup: "#2dd4bf",
	reset_10: "#859490",
};

const MARKER_LABELS: Record<TripMarker["type"], string> = {
	break_30: "30-min break",
	current: "Current",
	dropoff: "Dropoff",
	fueling: "Fueling",
	pickup: "Pickup",
	reset_10: "10-hr reset",
};

const formatCoords = (lat: number, lng: number) => `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

const formatMiles = (miles: number) => `${miles.toFixed(1)} mi`;

const haversineMiles = (lat0: number, lng0: number, lat1: number, lng1: number) => {
	const radius = 3958.8;
	const toRad = (value: number) => (value * Math.PI) / 180;
	const dLat = toRad(lat1 - lat0);
	const dLng = toRad(lng1 - lng0);
	const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat0)) * Math.cos(toRad(lat1)) * Math.sin(dLng / 2) ** 2;
	return 2 * radius * Math.asin(Math.sqrt(a));
};

const splitRoute = (plan: TripPlanResponse) => {
	const coordinates = plan.route.coordinates;
	const cutoff = plan.route.cycle_exceeded_at_mile;
	if (cutoff == null || !plan.cycle_exceeded || coordinates.length < 2) {
		return { dashed: [] as [number, number][], solid: coordinates };
	}
	let traveled = 0;
	const solid: [number, number][] = [coordinates[0]];
	const dashed: [number, number][] = [];
	let switched = false;
	for (let index = 1; index < coordinates.length; index += 1) {
		const [lng0, lat0] = coordinates[index - 1];
		const [lng1, lat1] = coordinates[index];
		const segmentMiles = haversineMiles(lat0, lng0, lat1, lng1);
		if (!switched && traveled + segmentMiles >= cutoff) {
			const ratio = segmentMiles === 0 ? 0 : (cutoff - traveled) / segmentMiles;
			const mid: [number, number] = [lng0 + (lng1 - lng0) * ratio, lat0 + (lat1 - lat0) * ratio];
			solid.push(mid);
			dashed.push(mid, coordinates[index]);
			switched = true;
		} else if (switched) {
			dashed.push(coordinates[index]);
		} else {
			solid.push(coordinates[index]);
		}
		traveled += segmentMiles;
	}
	return { dashed, solid };
};

const RouteMap = ({ plan }: RouteMapProps) => {
	const locationCache = useRef<Record<string, string>>({});
	const mapRef = useRef<MapRef>(null);
	const [isLoadingLocation, setIsLoadingLocation] = useState(false);
	const [resolvedLocation, setResolvedLocation] = useState<string | null>(null);
	const [selected, setSelected] = useState<SelectedCheckpoint | null>(null);
	const { dashed, solid } = useMemo(() => splitRoute(plan), [plan]);
	const bounds = useMemo(() => {
		const points = plan.route.coordinates;
		if (!points.length) {
			return { latitude: 39.8, longitude: -98.5, zoom: 3 };
		}
		const lngs = points.map((point) => point[0]);
		const lats = points.map((point) => point[1]);
		return {
			latitude: (Math.min(...lats) + Math.max(...lats)) / 2,
			longitude: (Math.min(...lngs) + Math.max(...lngs)) / 2,
			zoom: 4.5,
		};
	}, [plan.route.coordinates]);

	useEffect(() => {
		setResolvedLocation(null);
		setSelected(null);
	}, [plan]);

	useEffect(() => {
		if (!selected) {
			setIsLoadingLocation(false);
			setResolvedLocation(null);
			return;
		}

		const marker = selected.marker;
		const cacheKey = `${marker.lat.toFixed(5)},${marker.lng.toFixed(5)}`;
		const cached = locationCache.current[cacheKey];
		const knownLocation = marker.location?.trim() || "";
		const shouldReverse = ROUTE_STOP_TYPES.has(marker.type) || knownLocation.length < 8;

		if (cached) {
			setResolvedLocation(cached);
			setIsLoadingLocation(false);
			return;
		}

		if (!shouldReverse && knownLocation) {
			setResolvedLocation(knownLocation);
			setIsLoadingLocation(false);
			return;
		}

		if (knownLocation) {
			setResolvedLocation(knownLocation);
		}

		let cancelled = false;
		setIsLoadingLocation(true);
		reverseGeocode(marker.lat, marker.lng)
			.then((label) => {
				if (cancelled) {
					return;
				}
				locationCache.current[cacheKey] = label;
				setResolvedLocation(label);
			})
			.catch(() => {
				if (cancelled) {
					return;
				}
				setResolvedLocation(knownLocation || "Location unavailable");
			})
			.finally(() => {
				if (!cancelled) {
					setIsLoadingLocation(false);
				}
			});

		return () => {
			cancelled = true;
		};
	}, [selected]);

	const handleSelectCheckpoint = (marker: TripMarker, index: number) => {
		setSelected({ index, marker });
		mapRef.current?.flyTo({
			center: [marker.lng, marker.lat],
			duration: 900,
			essential: true,
			zoom: DETAIL_ZOOM,
		});
	};

	const handleClearSelection = () => {
		setSelected(null);
		mapRef.current?.flyTo({
			center: [bounds.longitude, bounds.latitude],
			duration: 900,
			essential: true,
			zoom: bounds.zoom,
		});
	};

	return (
		<div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container">
			<div className="flex flex-wrap gap-3 border-b border-outline-variant px-4 py-3">
				{(Object.keys(MARKER_LABELS) as TripMarker["type"][]).map((type) => (
					<span className="inline-flex items-center gap-2 font-mono text-[11px] text-on-surface-variant" key={type}>
						<span className="h-2.5 w-2.5 rounded-full" style={{ background: MARKER_COLORS[type] }} />
						{MARKER_LABELS[type]}
					</span>
				))}
			</div>
			{selected && (
				<div className="flex flex-wrap items-start justify-between gap-3 border-b border-outline-variant bg-surface-container-low px-4 py-3">
					<div className="min-w-0 flex-1">
						<p className="font-mono text-xs tracking-wider text-primary uppercase">
							{MARKER_LABELS[selected.marker.type]}
						</p>
						<p className="mt-1 text-sm leading-snug text-on-surface">
							{isLoadingLocation && !resolvedLocation
								? "Resolving location…"
								: resolvedLocation || selected.marker.location || selected.marker.label}
						</p>
						{isLoadingLocation && resolvedLocation && (
							<p className="mt-1 font-mono text-[10px] tracking-wider text-on-surface-variant uppercase">
								Refreshing place name…
							</p>
						)}
						<dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs text-on-surface-variant sm:grid-cols-3">
							<div>
								<dt className="font-mono uppercase tracking-wider">Activity</dt>
								<dd className="mt-0.5 text-on-surface">{selected.marker.label}</dd>
							</div>
							<div>
								<dt className="font-mono uppercase tracking-wider">Day</dt>
								<dd className="mt-0.5 font-mono text-on-surface">{selected.marker.day_index + 1}</dd>
							</div>
							<div>
								<dt className="font-mono uppercase tracking-wider">Miles so far</dt>
								<dd className="mt-0.5 font-mono text-on-surface">
									{formatMiles(selected.marker.cumulative_miles)}
								</dd>
							</div>
							<div className="col-span-2 sm:col-span-3">
								<dt className="font-mono uppercase tracking-wider">Coordinates</dt>
								<dd className="mt-0.5 font-mono text-on-surface">
									{formatCoords(selected.marker.lat, selected.marker.lng)}
								</dd>
							</div>
						</dl>
					</div>
					<button
						className="rounded-sm border border-outline-variant px-2.5 py-1.5 font-mono text-[11px] tracking-wider text-on-surface-variant uppercase hover:border-primary hover:text-primary"
						onClick={handleClearSelection}
						type="button">
						Close
					</button>
				</div>
			)}
			<div className="h-105 w-full">
				<Map
					initialViewState={bounds}
					mapStyle={MAP_STYLE}
					onClick={handleClearSelection}
					ref={mapRef}
					style={{ height: "100%", width: "100%" }}>
					{solid.length > 1 && (
						<Source
							data={{ type: "Feature", geometry: { type: "LineString", coordinates: solid }, properties: {} }}
							id="route-solid"
							type="geojson">
							<Layer
								id="route-solid-line"
								paint={{ "line-color": "#2dd4bf", "line-opacity": 0.95, "line-width": 4 }}
								type="line"
							/>
						</Source>
					)}
					{dashed.length > 1 && (
						<Source
							data={{ type: "Feature", geometry: { type: "LineString", coordinates: dashed }, properties: {} }}
							id="route-dashed"
							type="geojson">
							<Layer
								id="route-dashed-line"
								paint={{
									"line-color": "#2dd4bf",
									"line-dasharray": [1.5, 1.5],
									"line-opacity": 0.35,
									"line-width": 4,
								}}
								type="line"
							/>
						</Source>
					)}
					{plan.markers.map((marker, index) => {
						const isSelected = selected?.index === index;
						return (
							<Marker
								anchor="bottom"
								key={`${marker.type}-${index}`}
								latitude={marker.lat}
								longitude={marker.lng}
								onClick={(event) => {
									event.originalEvent.stopPropagation();
									handleSelectCheckpoint(marker, index);
								}}
								style={{ cursor: "pointer" }}>
								<button className="flex flex-col items-center gap-1 border-0 bg-transparent p-0" type="button">
									<span
										className={`max-w-40 truncate rounded-sm border px-1.5 py-0.5 font-mono text-[10px] tracking-wide ${
											isSelected
												? "border-primary bg-surface-container-lowest text-primary"
												: "border-outline-variant bg-surface-container-lowest/95 text-on-surface"
										}`}
										title={marker.location || marker.label}>
										{MARKER_LABELS[marker.type]}
									</span>
									<span
										className={`h-3.5 w-3.5 rounded-full border ${
											isSelected
												? "border-primary ring-2 ring-primary/40"
												: "border-surface-container-lowest"
										}`}
										style={{ background: MARKER_COLORS[marker.type] }}
									/>
								</button>
							</Marker>
						);
					})}
				</Map>
			</div>
		</div>
	);
};

export default RouteMap;
