import { useEffect, useId, useRef, useState } from "react";

import { type LocationSuggestion, suggestLocations } from "../api/trips";

type LocationInputProps = {
	label: string;
	onChange: (value: string) => void;
	placeholder: string;
	value: string;
};

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 3;

const LocationInput = ({ label, onChange, placeholder, value }: LocationInputProps) => {
	const blurTimer = useRef<number | null>(null);
	const listId = useId();
	const requestId = useRef(0);
	const skipNextSearch = useRef(false);
	const [isOpen, setIsOpen] = useState(false);
	const [isSearching, setIsSearching] = useState(false);
	const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);

	useEffect(() => {
		if (skipNextSearch.current) {
			skipNextSearch.current = false;
			setIsOpen(false);
			setIsSearching(false);
			setSuggestions([]);
			return;
		}

		const query = value.trim();
		if (query.length < MIN_QUERY_LENGTH) {
			setIsOpen(false);
			setIsSearching(false);
			setSuggestions([]);
			return;
		}

		const timer = window.setTimeout(async () => {
			const currentRequest = ++requestId.current;
			setIsSearching(true);
			try {
				const results = await suggestLocations(query);
				if (currentRequest !== requestId.current) {
					return;
				}
				setSuggestions(results);
				setIsOpen(true);
			} catch {
				if (currentRequest !== requestId.current) {
					return;
				}
				setSuggestions([]);
			} finally {
				if (currentRequest === requestId.current) {
					setIsSearching(false);
				}
			}
		}, DEBOUNCE_MS);

		return () => window.clearTimeout(timer);
	}, [value]);

	const clearBlurTimer = () => {
		if (blurTimer.current !== null) {
			window.clearTimeout(blurTimer.current);
			blurTimer.current = null;
		}
	};

	const handleBlur = () => {
		blurTimer.current = window.setTimeout(() => setIsOpen(false), 150);
	};

	const handleFocus = () => {
		clearBlurTimer();
		if (suggestions.length > 0) {
			setIsOpen(true);
		}
	};

	const handleSelect = (suggestion: LocationSuggestion) => {
		clearBlurTimer();
		skipNextSearch.current = true;
		requestId.current += 1;
		onChange(suggestion.label);
		setIsOpen(false);
		setIsSearching(false);
		setSuggestions([]);
	};

	return (
		<div className="relative flex flex-col gap-2">
			<label className="flex flex-col gap-2">
				<span className="font-mono text-xs tracking-wider text-on-surface-variant uppercase">{label}</span>
				<input
					aria-autocomplete="list"
					aria-controls={listId}
					aria-expanded={isOpen && suggestions.length > 0}
					autoComplete="off"
					className="rounded-sm border border-outline-variant bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface outline-none focus:border-primary-container"
					onBlur={handleBlur}
					onChange={(event) => onChange(event.target.value)}
					onFocus={handleFocus}
					onKeyDown={(event) => {
						if (event.key === "Escape") {
							setIsOpen(false);
						}
					}}
					placeholder={placeholder}
					required
					role="combobox"
					value={value}
				/>
			</label>
			{isOpen && (suggestions.length > 0 || isSearching) && (
				<ul
					className="absolute top-full z-20 mt-1 max-h-56 w-full overflow-auto rounded-sm border border-outline-variant bg-surface-container-high py-1 shadow-none"
					id={listId}
					role="listbox">
					{isSearching && suggestions.length === 0 ? (
						<li className="px-3 py-2 text-sm text-on-surface-variant">Searching…</li>
					) : (
						suggestions.map((suggestion) => (
							<li key={`${suggestion.label},${suggestion.lat},${suggestion.lng}`}>
								<button
									className="w-full px-3 py-2 text-left text-sm text-on-surface hover:bg-surface-container-highest focus:bg-surface-container-highest focus:outline-none"
									onClick={() => handleSelect(suggestion)}
									onMouseDown={(event) => event.preventDefault()}
									role="option"
									type="button">
									{suggestion.label}
								</button>
							</li>
						))
					)}
				</ul>
			)}
		</div>
	);
};

export default LocationInput;
