<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
import {
  resolveTransformErrorTarget,
  scrollToHelperField,
  type PlatformFieldIndex,
  type TransformErrorEntry,
} from "$lib/transformErrors";

  type Props = {
    errors: Record<string, TransformErrorEntry[]>;
    mappingIndex: PlatformFieldIndex;
    questionById: Map<string, string>;
    onEdit?: () => void;
  };

  let { errors, mappingIndex, questionById, onEdit }: Props = $props();
</script>

<section class="rounded-xl border border-destructive/30 bg-destructive/5 p-4">
  <h3 class="font-heading font-bold text-destructive">Could not generate some platform answers</h3>
  <p class="mt-1 text-sm text-muted-foreground">
    Fix the helper fields below, then generate again.
  </p>
  <ul class="mt-4 space-y-4 text-sm">
    {#each Object.entries(errors) as [platformFieldId, entries] (platformFieldId)}
      {@const target = resolveTransformErrorTarget(platformFieldId, mappingIndex, questionById)}
      <li class="surface-card rounded-lg border-destructive/20 p-3">
        <p class="font-medium text-card-foreground">{target.platformLabel}</p>
        {#if target.helperLabels.length > 0}
          <p class="mt-1 text-card-muted-foreground">
            Check:
            {#each target.helperLabels as label, i (label)}
              {i > 0 ? ", " : ""}<span class="text-card-foreground">{label}</span>
            {/each}
            {#if target.sectionLabel}
              <span class="text-card-muted-foreground"> ({target.sectionLabel})</span>
            {/if}
          </p>
          <div class="mt-2 flex flex-wrap gap-2">
            {#each target.helperQuestionIds as helperId (helperId)}
              <Button
                variant="outline"
                size="sm"
                type="button"
                onclick={() => {
                  onEdit?.();
                  scrollToHelperField(helperId);
                }}
              >
                Go to field
              </Button>
            {/each}
          </div>
        {/if}
        <ul class="mt-2 list-inside list-disc text-card-muted-foreground">
          {#each entries as { message } (message)}
            <li>{message}</li>
          {/each}
        </ul>
      </li>
    {/each}
  </ul>
</section>
