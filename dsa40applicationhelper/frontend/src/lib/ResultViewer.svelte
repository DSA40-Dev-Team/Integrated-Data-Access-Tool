<script lang="ts">
  import * as Tabs from "$lib/components/ui/tabs/index.ts";
  import { Separator } from "$lib/components/ui/separator/index.ts";
  import { Button } from "$lib/components/ui/button/index.ts";
  import { Checkmark, Clipboard } from "./components/icons/Icons.svelte";
  import { toasts } from "$lib/toast";

  type Answer = {
    question_id: string;
    text: string;
    value: string;
  };

  type Result = {
    name: string;
    answers: Answer[];
  };

  export type PlatformRef = {
    id: string;
    name: string;
    applicationLink?: string;
    modality?: string;
  };

  type Props = {
    results: Result[];
    platforms?: PlatformRef[];
  };

  let { results, platforms = [] }: Props = $props();

  const platformById = $derived(new Map(platforms.map((platform) => [platform.id, platform])));

  const enrichedResults = $derived(
    results.map((result) => {
      const platform = platformById.get(result.name);
      return {
        ...result,
        displayName: platform?.name ?? result.name,
        platform,
      };
    }),
  );

  let tabs = $derived(enrichedResults.map((entry) => entry.name));
  let copiedId = $state<string | null>(null);

  function applicationHref(platform: PlatformRef | undefined): string | null {
    const link = platform?.applicationLink?.trim();
    if (!link) return null;
    if (/^https?:\/\//i.test(link)) return link;
    if (link.includes("@")) return `mailto:${link}`;
    return link.startsWith("mailto:") ? link : null;
  }

  function applicationLinkLabel(platform: PlatformRef | undefined): string {
    if (!platform) return "Open application";
    const href = applicationHref(platform);
    if (href?.startsWith("mailto:")) return `Email ${platform.name} application`;
    if (platform.modality === "email") return `Contact ${platform.name}`;
    return `Open ${platform.name} form`;
  }

  async function copyToClipboard(value: string, uniqueId: string, successMessage: string) {
    await navigator.clipboard.writeText(value);
    copiedId = uniqueId;
    toasts.show(successMessage, "success");
    setTimeout(() => {
      copiedId = null;
    }, 1500);
  }
</script>

<div class="flex w-full max-w-3xl flex-col gap-6">
  <Tabs.Root value={tabs[0]}>
    <Tabs.List variant="line" class="text-card-muted-foreground">
      {#each enrichedResults as entry (entry.name)}
        <Tabs.Trigger value={entry.name} class="results-tabs-trigger">
          {entry.displayName}
        </Tabs.Trigger>
      {/each}
    </Tabs.List>

    {#each enrichedResults as vlopse (vlopse.name)}
      <Tabs.Content value={vlopse.name}>
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-field-border bg-white p-3">
          <p class="text-sm text-card-muted-foreground">
            {vlopse.answers.length} answer{vlopse.answers.length === 1 ? "" : "s"} — copy each one
            into the platform form
          </p>
          {#if applicationHref(vlopse.platform)}
            <Button
              href={applicationHref(vlopse.platform)!}
              target="_blank"
              rel="noopener noreferrer"
              size="lg"
              class="btn-collaboratory shrink-0"
            >
              {applicationLinkLabel(vlopse.platform)}
            </Button>
          {/if}
        </div>

        {#each vlopse.answers as answer, i (answer.question_id)}
          {#if i > 0}
            <Separator class="bg-field-border" />
          {/if}
          <div class="flex items-start justify-between gap-4 py-3">
            <div class="flex min-w-0 flex-col gap-2">
              <p class="font-heading text-base font-bold text-collaboratory-navy">{answer.text}</p>
              <p class="whitespace-pre-wrap text-sm text-card-foreground">{answer.value}</p>
            </div>
            <Button
              variant="outline"
              size="icon-sm"
              onclick={() =>
                copyToClipboard(
                  answer.value,
                  vlopse.name + ":" + answer.question_id,
                  "Answer copied",
                )}
              aria-label="Copy answer for {answer.text}"
              class="mt-0.5 shrink-0"
            >
              {#if copiedId === vlopse.name + ":" + answer.question_id}
                {@render Clipboard()}
              {:else}
                {@render Checkmark()}
              {/if}
            </Button>
          </div>
        {/each}
      </Tabs.Content>
    {/each}
  </Tabs.Root>
</div>
