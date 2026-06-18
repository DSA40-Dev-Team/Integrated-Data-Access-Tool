<script lang="ts">
  import { onMount } from "svelte";
  import { Button } from "$lib/components/ui/button/index.js";

  import { goto } from "$app/navigation";
  import { apiQuestionsApplicableQuestions, apiVlopseGetVlopse } from "@api";

  type PlatformEntry = {
    id: string;
    name: string;
    questionCount: number | null;
  };

  let platforms: PlatformEntry[] = $state([]);
  let error: string | null = $state(null);
  let loading = $state(true);

  let selected = $state<string[]>([]);

  async function loadQuestionCount(platformId: string): Promise<number> {
    const call = await apiQuestionsApplicableQuestions({
      query: { vlopse: [platformId] },
    });
    if (!call.response.ok) throw new Error(`HTTP ${call.response.status}`);
    return call.data?.length ?? 0;
  }

  onMount(async () => {
    try {
      const call = await apiVlopseGetVlopse();
      const response = call.response;

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const vlopses = call.data ?? [];

      platforms = await Promise.all(
        vlopses.map(async (vlopse) => {
          try {
            const questionCount = await loadQuestionCount(vlopse.id);
            return { id: vlopse.id, name: vlopse.info.name, questionCount };
          } catch {
            return { id: vlopse.id, name: vlopse.info.name, questionCount: null };
          }
        }),
      );
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  function togglePlatform(id: string) {
    if (selected.includes(id)) {
      selected = selected.filter((item) => item !== id);
    } else {
      selected = [...selected, id];
    }
  }

  function questionCountLabel(count: number | null): string {
    if (count === null) return "Questions unavailable";
    return `${count} question${count === 1 ? "" : "s"}`;
  }

  function submit() {
    if (selected.length === 0) return;
    const params = new URLSearchParams(selected.map((v) => ["vlopses", v]));
    goto(`/helper/form?${params}`);
  }
</script>

<svelte:head>
  <title>Select platforms · DSA40 Application Helper</title>
</svelte:head>

<div class="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
  <h1 class="font-heading text-2xl font-bold tracking-tight sm:text-3xl">Select platforms</h1>
  <p class="mt-2 text-muted-foreground">
    Choose the VLOPSE platforms you are applying to. You will answer shared questions once.
  </p>

  {#if error}
    <p
      class="mt-6 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
    >
      {error}
    </p>
  {:else if loading}
    <p class="mt-6 text-sm text-muted-foreground">Loading platforms…</p>
  {:else}
    <ul class="mt-8 grid gap-3 sm:grid-cols-2" role="list">
      {#each platforms as platform (platform.id)}
        {@const isSelected = selected.includes(platform.id)}
        <li>
          <button
            type="button"
            class="flex w-full cursor-pointer items-start gap-4 p-4 text-left transition-[border-color,box-shadow,background-color] {isSelected
              ? 'surface-card border-l-4 border-l-primary ring-1 ring-primary/25 hover:shadow-md'
              : 'surface-panel hover:border-primary/40 hover:bg-[rgb(52_64_88/95%)]'}"
            aria-pressed={isSelected}
            onclick={() => togglePlatform(platform.id)}
          >
            <span
              class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded border {isSelected
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-panel-border bg-transparent'}"
              aria-hidden="true"
            >
              {#if isSelected}
                <svg viewBox="0 0 12 12" class="size-3" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2 6l3 3 5-5" />
                </svg>
              {/if}
            </span>
            <span class="min-w-0 flex-1">
              <span class="font-heading block font-bold">{platform.name}</span>
              <span
                class="mt-1 block text-sm {isSelected
                  ? 'text-card-muted-foreground'
                  : 'text-muted-foreground'}"
              >
                {questionCountLabel(platform.questionCount)}
              </span>
            </span>
          </button>
        </li>
      {/each}
    </ul>

    <div class="mt-8 flex flex-wrap items-center gap-4">
      <Button onclick={submit} disabled={selected.length === 0} size="lg" class="btn-collaboratory">
        Continue to form
      </Button>
      {#if selected.length > 0}
        <p class="text-sm text-muted-foreground">
          {selected.length} platform{selected.length === 1 ? "" : "s"} selected
        </p>
      {/if}
    </div>
  {/if}
</div>
