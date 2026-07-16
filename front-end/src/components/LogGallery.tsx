import { useEffect, useState } from "react";

import type { TripLog } from "../types/trip";

type LogGalleryProps = {
	logs: TripLog[];
};

const CloseIcon = () => (
	<svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
		<path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
	</svg>
);

const ExpandIcon = () => (
	<svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 24 24">
		<path
			d="M9 4H4v5M15 4h5v5M9 20H4v-5M20 15v5h-5"
			stroke="currentColor"
			strokeLinecap="round"
			strokeLinejoin="round"
			strokeWidth="2"
		/>
	</svg>
);

const LogGallery = ({ logs }: LogGalleryProps) => {
	const [activeIndex, setActiveIndex] = useState(0);
	const [isPreviewOpen, setIsPreviewOpen] = useState(false);

	useEffect(() => {
		if (!isPreviewOpen) {
			return;
		}
		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setIsPreviewOpen(false);
			}
		};
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [isPreviewOpen]);

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
			<div className="relative mx-auto w-fit max-w-full rounded-md border border-outline-variant bg-surface-container-lowest p-1">
				<button
					aria-label="Open log sheet full preview"
					className="absolute top-3 right-3 z-10 rounded-sm border border-outline-variant bg-surface-container p-2 text-on-surface transition-colors hover:border-primary-container hover:text-primary"
					onClick={() => setIsPreviewOpen(true)}
					type="button">
					<ExpandIcon />
				</button>
				<img
					alt={active.date_label}
					className="block h-auto w-full max-w-full object-contain"
					src={active.image_base64}
				/>
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
						<img alt={log.date_label} className="h-20 w-auto object-contain" src={log.image_base64} />
						<p className="mt-1 font-mono text-[10px] text-on-surface-variant">{log.date_label}</p>
					</button>
				))}
			</div>
			{isPreviewOpen ? (
				<div
					aria-modal="true"
					className="fixed inset-0 z-50 flex items-center justify-center bg-surface-container-lowest/95 p-2 sm:p-3"
					onClick={() => setIsPreviewOpen(false)}
					role="dialog">
					<div
						className="flex h-full max-h-[calc(100dvh-1rem)] w-full max-w-[calc(100vw-1rem)] flex-col rounded-lg border border-primary/10 bg-surface-container p-2 sm:p-3"
						onClick={(event) => event.stopPropagation()}>
						<div className="mb-2 flex shrink-0 items-center justify-between gap-3">
							<p className="font-mono text-xs tracking-wider text-primary uppercase">{active.date_label}</p>
							<button
								aria-label="Close full preview"
								className="rounded-sm border border-outline-variant p-2 text-on-surface transition-colors hover:border-primary-container hover:text-primary"
								onClick={() => setIsPreviewOpen(false)}
								type="button">
								<CloseIcon />
							</button>
						</div>
						<div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-md bg-surface-container-lowest">
							<img alt={active.date_label} className="h-full w-full object-contain" src={active.image_base64} />
						</div>
					</div>
				</div>
			) : null}
		</section>
	);
};

export default LogGallery;
