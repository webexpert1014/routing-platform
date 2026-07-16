import { useState, type FormEvent } from "react";

import LocationInput from "./LocationInput";

type TripFormProps = {
	isLoading: boolean;
	onSubmit: (values: {
		current_cycle_used: number;
		current_location: string;
		dropoff_location: string;
		pickup_location: string;
	}) => void;
};

const TripForm = ({ isLoading, onSubmit }: TripFormProps) => {
	const [currentCycleUsed, setCurrentCycleUsed] = useState("0");
	const [currentLocation, setCurrentLocation] = useState("");
	const [dropoffLocation, setDropoffLocation] = useState("");
	const [pickupLocation, setPickupLocation] = useState("");

	const handleSubmit = (event: FormEvent) => {
		event.preventDefault();
		onSubmit({
			current_cycle_used: Number(currentCycleUsed),
			current_location: currentLocation.trim(),
			dropoff_location: dropoffLocation.trim(),
			pickup_location: pickupLocation.trim(),
		});
	};

	return (
		<form
			className="flex h-full min-h-105 flex-col rounded-lg border border-outline-variant bg-surface-container p-6"
			onSubmit={handleSubmit}>
			<div>
				<p className="font-mono text-xs tracking-wider text-primary uppercase">Trip inputs</p>
				<h2 className="mt-2 text-xl font-semibold tracking-tight text-on-surface">Plan HOS route</h2>
				<p className="mt-1 text-sm text-on-surface-variant">
					Current → Pickup → Dropoff with FMCSA 70/8 rules and daily log sheets.
				</p>
			</div>
			<div className="mt-6 flex flex-col gap-4">
				<LocationInput
					label="Current location"
					onChange={setCurrentLocation}
					placeholder="Chicago, IL"
					value={currentLocation}
				/>
				<LocationInput
					label="Pickup location"
					onChange={setPickupLocation}
					placeholder="Indianapolis, IN"
					value={pickupLocation}
				/>
				<LocationInput
					label="Dropoff location"
					onChange={setDropoffLocation}
					placeholder="Atlanta, GA"
					value={dropoffLocation}
				/>
				<label className="flex flex-col gap-2">
					<span className="font-mono text-xs tracking-wider text-on-surface-variant uppercase">
						Current cycle used (hours)
					</span>
					<input
						className="rounded-sm border border-outline-variant bg-surface-container-lowest px-3 py-2.5 font-mono text-sm text-on-surface outline-none focus:border-primary-container"
						max={70}
						min={0}
						onChange={(event) => setCurrentCycleUsed(event.target.value)}
						required
						step={0.25}
						type="number"
						value={currentCycleUsed}
					/>
				</label>
			</div>
			<div aria-hidden className="min-h-8 flex-1" />
			<button
				className="w-full shrink-0 rounded-sm bg-primary-container px-4 py-3 text-sm font-semibold text-on-primary transition disabled:opacity-50"
				disabled={isLoading}
				type="submit">
				{isLoading ? "Calculating route…" : "Calculate compliant route"}
			</button>
		</form>
	);
};

export default TripForm;
