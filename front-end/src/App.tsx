import { useState } from "react";

import { planTrip, readApiError } from "./api/trips";
import LogGallery from "./components/LogGallery";
import RouteMap from "./components/RouteMap";
import TripForm from "./components/TripForm";
import type { TripPlanResponse } from "./types/trip";

const App = () => {
	const [error, setError] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [plan, setPlan] = useState<TripPlanResponse | null>(null);

	const handleSubmit = async (values: {
		current_cycle_used: number;
		current_location: string;
		dropoff_location: string;
		pickup_location: string;
	}) => {
		setIsLoading(true);
		setError(null);
		setPlan(null);
		try {
			const response = await planTrip(values);
			setPlan(response);
		} catch (caught) {
			setError(readApiError(caught));
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-full bg-background text-on-surface">
			<header className="border-b border-outline-variant bg-surface-container-low">
				<div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-5 md:px-8">
					<div className="flex items-center gap-3">
						<img alt="" className="size-10 shrink-0" height={40} src="/logo.svg" width={40} />
						<div>
							<p className="font-mono text-xs tracking-[0.08em] text-primary uppercase">HOS</p>
							<h1 className="mt-1 text-2xl font-semibold tracking-tight">Routing Platform</h1>
						</div>
					</div>
					<p className="hidden max-w-sm text-right text-sm text-on-surface-variant md:block">
						70-hour / 8-day property-carrying rules · OSM routing · daily paper logs
					</p>
				</div>
			</header>
			<main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 md:px-8">
				<section className="grid min-h-105 gap-6 lg:grid-cols-[360px_1fr] lg:items-stretch">
					<TripForm isLoading={isLoading} onSubmit={handleSubmit} />
					{plan ? (
						<RouteMap plan={plan} />
					) : (
						<div className="flex h-full min-h-105 items-center justify-center rounded-lg border border-dashed border-outline-variant bg-surface-container-low px-6 text-center text-sm text-on-surface-variant">
							Enter trip details to generate an HOS-aware route map and daily log sheets.
						</div>
					)}
				</section>
				{error && (
					<div className="rounded-lg border border-error/40 bg-surface-container px-4 py-3 text-sm text-error">
						{error}
					</div>
				)}
				{plan && (
					<section className="grid gap-6 lg:grid-cols-[360px_1fr] lg:items-start">
						<div className="rounded-lg border border-outline-variant bg-surface-container p-4">
							<p className="font-mono text-xs tracking-wider text-on-surface-variant uppercase">Summary</p>
							<dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
								<div>
									<dt className="text-on-surface-variant">Available cycle</dt>
									<dd className="font-mono text-primary">{plan.available_cycle_hours.toFixed(2)} h</dd>
								</div>
								<div>
									<dt className="text-on-surface-variant">Total miles</dt>
									<dd className="font-mono">{plan.summary.total_miles}</dd>
								</div>
								<div>
									<dt className="text-on-surface-variant">Drive hours</dt>
									<dd className="font-mono">{plan.summary.total_drive_hours}</dd>
								</div>
								<div>
									<dt className="text-on-surface-variant">Log days</dt>
									<dd className="font-mono">{plan.summary.days_count}</dd>
								</div>
							</dl>
							{plan.cycle_warning && (
								<p className="mt-3 border-t border-outline-variant pt-3 text-sm text-[#ffac5a]">
									{plan.cycle_warning}
								</p>
							)}
						</div>
						<LogGallery logs={plan.logs} />
					</section>
				)}
			</main>
		</div>
	);
};

export default App;
