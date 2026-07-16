import { useState } from "react";

import type { TripLog } from "../types/trip";

type LogGalleryProps = {
	logs: TripLog[];
};

const LogGallery = ({ logs }: LogGalleryProps) => {
	const [activeIndex, setActiveIndex] = useState(0);
	if (!logs.length) {
		return null;
	}
	const active = logs[Math.min(activeIndex, logs.length - 1)];

	return (
		<section className="rounded-lg border border-outline-variant bg-surface-container p-6">
			<div className="mb-4 flex flex-wrap items-end justify-between gap-3">
				<div>
					<p className="font-mono text-xs tracking-wider text-primary uppercase">Daily logs</p>
					<h2 className="mt-2 text-xl font-semibold text-on-surface">Generated log sheets</h2>
				</div>
				<div className="flex items-center gap-2">
					<button
						className="rounded-sm border border-outline-variant px-3 py-1.5 text-sm text-on-surface disabled:opacity-40"
						disabled={activeIndex <= 0}
						onClick={() => setActiveIndex((index) => Math.max(0, index - 1))}
						type="button">
						Prev
					</button>
					<span className="font-mono text-xs text-on-surface-variant">
						{activeIndex + 1} / {logs.length}
					</span>
					<button
						className="rounded-sm border border-outline-variant px-3 py-1.5 text-sm text-on-surface disabled:opacity-40"
						disabled={activeIndex >= logs.length - 1}
						onClick={() => setActiveIndex((index) => Math.min(logs.length - 1, index + 1))}
						type="button">
						Next
					</button>
				</div>
			</div>
			<div className="overflow-hidden rounded-md border border-outline-variant bg-surface-container-lowest p-3">
				<img alt={active.date_label} className="mx-auto max-h-160 w-full object-contain" src={active.image_base64} />
			</div>
			<div className="mt-4 flex gap-2 overflow-x-auto pb-1">
				{logs.map((log, index) => (
					<button
						className={`shrink-0 rounded-sm border px-2 py-2 ${
							index === activeIndex
								? "border-primary-container bg-surface-container-high"
								: "border-outline-variant bg-surface-container-low"
						}`}
						key={log.day_index}
						onClick={() => setActiveIndex(index)}
						type="button">
						<img alt={log.date_label} className="h-20 w-28 object-cover" src={log.image_base64} />
						<p className="mt-1 font-mono text-[10px] text-on-surface-variant">{log.date_label}</p>
					</button>
				))}
			</div>
		</section>
	);
};

export default LogGallery;
