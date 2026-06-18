<script lang="ts">
  import type { SectionStats } from "$lib/formSections";
  import CheckIcon from "@lucide/svelte/icons/check";
  import CircleIcon from "@lucide/svelte/icons/circle";
  import CircleDotIcon from "@lucide/svelte/icons/circle-dot";
  import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";

  type SectionStatus = "complete" | "partial" | "empty" | "error";

  type Props = {
    sections: SectionStats[];
    activeSectionId?: string | null;
    showReview?: boolean;
    reviewActive?: boolean;
    reviewReady?: boolean;
    onSelect?: (sectionId: string) => void;
    onReviewSelect?: () => void;
  };

  let {
    sections,
    activeSectionId = null,
    showReview = false,
    reviewActive = false,
    reviewReady = false,
    onSelect,
    onReviewSelect,
  }: Props = $props();

  function sectionStatus(stat: SectionStats): SectionStatus {
    if (stat.errorCount > 0) return "error";
    if (stat.requiredTotal > 0) {
      if (stat.requiredFilled >= stat.requiredTotal) return "complete";
      return stat.requiredFilled > 0 ? "partial" : "empty";
    }
    if (stat.filled === 0) return "empty";
    if (stat.filled < stat.total) return "partial";
    return "complete";
  }

  const statusLabel: Record<SectionStatus, string> = {
    complete: "Complete",
    partial: "In progress",
    empty: "Not started",
    error: "Has issues",
  };
</script>

{#if sections.length > 0}
  <nav aria-label="Form sections" class="form-section-nav">
    <p class="mb-3 hidden text-xs font-medium uppercase tracking-wide text-foreground/70 lg:block">
      Sections
    </p>
    <ol class="flex flex-row gap-2 overflow-x-auto pb-1 lg:flex-col lg:gap-0.5 lg:overflow-visible lg:pb-0">
      {#each sections as section (section.id)}
        {@const status = sectionStatus(section)}
        <li class="shrink-0 lg:shrink">
          <button
            type="button"
            class="flex w-full min-w-[9rem] items-start gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors lg:min-w-0 lg:px-2.5 lg:py-2 {activeSectionId ===
            section.id
              ? 'border-l-4 border-l-primary bg-primary/15 text-foreground ring-1 ring-primary/25 lg:ring-0'
              : 'surface-panel text-foreground/90 hover:border-primary/40 lg:border-transparent lg:bg-transparent lg:hover:bg-white/8 lg:hover:text-foreground'}"
            aria-current={activeSectionId === section.id ? "step" : undefined}
            onclick={() => onSelect?.(section.id)}
          >
            <span
              class="mt-0.5 flex size-4 shrink-0 items-center justify-center {status === 'complete'
                ? 'text-primary'
                : status === 'partial'
                  ? 'text-amber-400'
                  : status === 'error'
                    ? 'text-destructive'
                    : 'text-foreground/45'}"
              aria-hidden="true"
            >
              {#if status === "complete"}
                <CheckIcon class="size-4" strokeWidth={2.5} />
              {:else if status === "partial"}
                <CircleDotIcon class="size-4" />
              {:else if status === "error"}
                <AlertCircleIcon class="size-4" />
              {:else}
                <CircleIcon class="size-4" />
              {/if}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block font-medium leading-snug">{section.label}</span>
              <span class="mt-0.5 block text-xs text-foreground/65">
                {#if section.requiredTotal > 0}
                  {section.requiredFilled} / {section.requiredTotal} required
                {:else if section.total > 0}
                  {section.filled} / {section.total} fields
                {/if}
                {#if section.requiredTotal > 0 || section.total > 0}
                  · {statusLabel[status]}
                {:else}
                  {statusLabel[status]}
                {/if}
              </span>
            </span>
          </button>
        </li>
      {/each}

      {#if showReview}
        <li class="shrink-0 lg:mt-2 lg:shrink lg:border-t lg:border-panel-border lg:pt-2">
          <button
            type="button"
            class="flex w-full min-w-[9rem] items-start gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors lg:min-w-0 lg:px-2.5 lg:py-2 {reviewActive
              ? 'border-l-4 border-l-primary bg-primary/15 text-foreground ring-1 ring-primary/25 lg:ring-0'
              : 'surface-panel text-foreground/90 hover:border-primary/40 lg:border-transparent lg:bg-transparent lg:hover:bg-white/8 lg:hover:text-foreground'}"
            aria-current={reviewActive ? "step" : undefined}
            onclick={() => onReviewSelect?.()}
          >
            <span
              class="mt-0.5 flex size-4 shrink-0 items-center justify-center {reviewReady
                ? 'text-primary'
                : 'text-foreground/45'}"
              aria-hidden="true"
            >
              {#if reviewReady}
                <CheckIcon class="size-4" strokeWidth={2.5} />
              {:else}
                <CircleIcon class="size-4" />
              {/if}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block font-medium leading-snug">Review & generate</span>
              <span class="mt-0.5 block text-xs text-foreground/65">
                {reviewReady ? "Ready to submit" : "Required fields missing"}
              </span>
            </span>
          </button>
        </li>
      {/if}
    </ol>
  </nav>
{/if}
