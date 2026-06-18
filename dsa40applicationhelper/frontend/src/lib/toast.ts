import { writable } from "svelte/store";

export type ToastVariant = "default" | "success";

export type ToastItem = {
	id: string;
	message: string;
	variant: ToastVariant;
};

function createToastStore() {
	const { subscribe, update } = writable<ToastItem[]>([]);

	function dismiss(id: string) {
		update((items) => items.filter((item) => item.id !== id));
	}

	function show(message: string, variant: ToastVariant = "default", durationMs = 2500) {
		const id = crypto.randomUUID();
		update((items) => [...items, { id, message, variant }]);
		setTimeout(() => dismiss(id), durationMs);
	}

	return { subscribe, show, dismiss };
}

export const toasts = createToastStore();
