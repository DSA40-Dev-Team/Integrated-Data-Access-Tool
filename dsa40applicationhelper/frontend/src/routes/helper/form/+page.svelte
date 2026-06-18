<script lang="ts">
  import type { PageProps } from "./$types";
  import type { DsaQuestion } from "@api/types.gen";
  import { onMount, tick } from "svelte";
  import { enhance } from "$app/forms";
  import { goto } from "$app/navigation";

  import Question from "$lib/Question.svelte";
  import PlatformScopedGroup from "$lib/PlatformScopedGroup.svelte";
  import ResultViewer from "$lib/ResultViewer.svelte";
  import PlatformLegalNotice from "$lib/PlatformLegalNotice.svelte";
  import type { PlatformLegalInfo } from "$lib/platformLegal";
  import FormSection from "$lib/FormSection.svelte";
  import FormSectionNav from "$lib/FormSectionNav.svelte";
  import TransformationErrorPanel from "$lib/TransformationErrorPanel.svelte";
  import FormProgress from "$lib/FormProgress.svelte";
  import ConfirmDialog from "$lib/components/ConfirmDialog.svelte";
  import { Alert } from "$lib/components/ui/alert/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { toasts } from "$lib/toast";
  import { isVisible, type FormValues } from "$lib/conditions";
  import { expandFormValues, migrateFlatFieldsIntoComposites } from "$lib/structured";
  import {
    buildFormRows,
    groupRowsBySection,
    sectionStatsForRows,
    FORM_SECTIONS,
    type FormRow,
  } from "$lib/formSections";
  import { formatPlatformLabel, platformNamesForIds } from "$lib/platformLabels";
  import { computeReadiness, createRequiredContext } from "$lib/formReadiness";
  import { pruneHiddenFieldValues } from "$lib/pruneHiddenValues";
  import {
    clearFormDraft,
    consumeMigrationSource,
    draftStorageKey,
    loadDraftByStorageKey,
    loadFormDraft,
    loadViewMode,
    markDraftForMigration,
    mergeDraftValues,
    saveFormDraft,
    saveViewMode,
    type FormViewMode,
  } from "$lib/formDraft";

  let { data, form }: PageProps = $props();

  function emptyValues(): FormValues {
    return Object.fromEntries(
      data.questions.map((q) => [
        q.id,
        q.input_type === "repeatable_group"
          ? "[]"
          : q.input_type === "composite_group"
            ? "{}"
            : "",
      ]),
    );
  }

  let values = $state<FormValues>(emptyValues());
  let showForm = $state(true);
  let generating = $state(false);
  let draftRestored = $state(false);
  let draftDismissed = $state(false);
  let migratedFrom = $state(false);
  let resultsAnchor: HTMLElement | undefined = $state();
  let formAnchor: HTMLElement | undefined = $state();
  let sectionOpen = $state<Record<string, boolean>>({});
  let viewMode = $state<FormViewMode>("wizard");
  let wizardStep = $state(0);
  let changePlatformsOpen = $state(false);

  const platformLegalInfo = $derived<PlatformLegalInfo[]>(
    data.platforms.map((platform) => ({
      id: platform.id,
      name: platform.name,
      applicationLink: platform.applicationLink,
      modality: platform.modality,
      disclaimers: platform.disclaimers ?? [],
      termImplications: platform.termImplications ?? [],
    })),
  );

  const questionById = $derived(
    new Map(data.questions.map((question) => [question.id, question.text])),
  );

  onMount(() => {
    viewMode = loadViewMode();

    let base = emptyValues();
    const migrateKey = consumeMigrationSource();
    if (migrateKey && migrateKey !== draftStorageKey(data.vlopseIds)) {
      const previous = loadDraftByStorageKey(migrateKey);
      if (previous) {
        base = mergeDraftValues(base, previous);
        migratedFrom = true;
      }
    }

    const draft = loadFormDraft(data.vlopseIds);
    if (draft) {
      values = migrateFlatFieldsIntoComposites(mergeDraftValues(base, draft));
      draftRestored = !migratedFrom;
    } else {
      values = migrateFlatFieldsIntoComposites(base);
    }
  });

  const submitValues = $derived(migrateFlatFieldsIntoComposites(values));

  $effect(() => {
    if (data.vlopseIds.length > 0) {
      saveFormDraft(data.vlopseIds, values);
    }
  });

  $effect(() => {
    if (form?.success) {
      values = pruneHiddenFieldValues(
        values,
        data.questions,
        data.conditions,
        data.vlopseIds,
      );
      showForm = false;
      tick().then(() => {
        resultsAnchor?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  });

  $effect(() => {
    if (form?.validation_errors?.length) {
      showForm = true;
      const ids = new Set(form.validation_errors.map((item) => item.question_id));
      for (const group of groupedSections) {
        const hasError = group.rows.some((row) =>
          rowQuestionIds(row).some((id) => ids.has(id)),
        );
        if (hasError) {
          sectionOpen = { ...sectionOpen, [group.section.id]: true };
        }
      }
      tick().then(() => {
        const firstError = form?.validation_errors?.[0]?.question_id;
        if (!firstError) return;
        if (viewMode === "wizard") {
          const sectionIdx = groupedSections.findIndex((group) =>
            group.rows.some((row) => rowQuestionIds(row).includes(firstError)),
          );
          if (sectionIdx >= 0) wizardStep = sectionIdx;
        }
        scrollToQuestion(firstError);
      });
    }
  });

  function rowQuestionIds(row: FormRow): string[] {
    if (row.kind === "platform_group") return row.variants.map((variant) => variant.id);
    return [row.question.id];
  }

  const formRows = $derived(
    buildFormRows(data.questions).map((row) => {
      if (row.kind !== "platform_group") return row;
      const names = platformNamesForIds(
        row.variants.map((variant) => variant.vlopse).filter(Boolean) as string[],
        data.platforms,
      );
      return {
        ...row,
        label: formatPlatformLabel(row.label, names),
      };
    }),
  );

  const groupedSections = $derived(groupRowsBySection(formRows));

  const visibility = $derived(
    Object.fromEntries(
      data.questions.map((q) => [
        q.id,
        isVisible(q.id, data.conditions, expandFormValues(values)),
      ]),
    ),
  );

  const errorIds = $derived(
    new Set((form?.validation_errors ?? []).map((item) => item.question_id)),
  );

  const requiredContext = $derived(createRequiredContext(data.requiredFields, data.questions));

  const sectionStats = $derived(
    sectionStatsForRows(formRows, visibility, values, errorIds, data.conditions, requiredContext),
  );

  const readiness = $derived(
    computeReadiness(formRows, visibility, values, data.conditions, requiredContext),
  );

  const progressFilled = $derived(
    sectionStats.reduce((sum, stat) => sum + stat.requiredFilled, 0),
  );

  const progressTotal = $derived(sectionStats.reduce((sum, stat) => sum + stat.requiredTotal, 0));

  const progressDetail = $derived(
    progressTotal > 0
      ? `${progressFilled} of ${progressTotal} required`
      : "No required fields",
  );

  const visibleCount = $derived(
    data.questions.filter((q) => visibility[q.id] || q.required).length,
  );

  const isReviewStep = $derived(
    viewMode === "wizard" && wizardStep >= groupedSections.length,
  );

  const activeWizardSection = $derived(
    viewMode === "wizard" && !isReviewStep ? groupedSections[wizardStep] : null,
  );

  const sectionLabelById = $derived(
    Object.fromEntries(FORM_SECTIONS.map((section) => [section.id, section.label])),
  );

  function scrollToQuestion(questionId: string) {
    document
      .querySelector(`[data-question-id="${questionId}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function scrollToSection(sectionId: string) {
    sectionOpen = { ...sectionOpen, [sectionId]: true };
    if (viewMode === "wizard") {
      const idx = groupedSections.findIndex((group) => group.section.id === sectionId);
      if (idx >= 0) wizardStep = idx;
      return;
    }
    document.getElementById(`section-${sectionId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function goToReviewStep() {
    wizardStep = groupedSections.length;
  }

  const activeSectionId = $derived(
    viewMode === "wizard" && !isReviewStep
      ? (activeWizardSection?.section.id ?? null)
      : null,
  );

  function setViewMode(mode: FormViewMode) {
    viewMode = mode;
    saveViewMode(mode);
    wizardStep = 0;
  }

  function discardDraft() {
    clearFormDraft(data.vlopseIds);
    values = emptyValues();
    draftRestored = false;
    migratedFrom = false;
    draftDismissed = true;
  }

  function changePlatforms() {
    changePlatformsOpen = true;
  }

  function confirmChangePlatforms() {
    markDraftForMigration(data.vlopseIds);
    goto("/helper");
  }

  function openFormForEditing() {
    showForm = true;
    if (viewMode === "wizard") {
      wizardStep = groupedSections.length;
    }
    tick().then(() => {
      formAnchor?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function toggleFormVisibility() {
    if (showForm) {
      showForm = false;
      return;
    }
    openFormForEditing();
  }

  function variantProps(variant: DsaQuestion) {
    return {
      id: variant.id,
      text: variant.text,
      required: variant.required,
      visible: visibility[variant.id],
      input_type: variant.input_type,
      help_text: variant.help_text,
      config: variant.config,
      options: variant.options,
      vlopse: variant.vlopse,
      validation: form?.validation_errors?.find((item) => item.question_id == variant.id)
        ?.description,
    };
  }

  function isStructuredQuestion(inputType: DsaQuestion["input_type"]): boolean {
    return inputType === "composite_group" || inputType === "repeatable_group";
  }
</script>

<svelte:head>
  <title>Application form · DSA40 Application Helper</title>
</svelte:head>

<div class="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">
  <div class="mb-8">
    <button
      type="button"
      class="text-sm text-muted-foreground transition-colors hover:text-foreground"
      onclick={changePlatforms}
    >
      ← Change platforms
    </button>
    <h1 class="font-heading mt-3 text-2xl font-bold tracking-tight sm:text-3xl">
      Application form
    </h1>
    <p class="mt-2 text-muted-foreground">
      {#if form?.success}
        Platform answers are ready — review the legal summary below, then copy answers into each platform form.
      {:else}
        {visibleCount} question{visibleCount === 1 ? "" : "s"} for your selection. Answers are saved
        automatically in this browser.
      {/if}
    </p>
  </div>

  {#if migratedFrom && !draftDismissed && !form?.success}
    <Alert variant="info" class="mb-6">
      Carried over answers that still apply to this platform selection.
    </Alert>
  {/if}

  {#if draftRestored && !draftDismissed && !form?.success}
    <Alert variant="info" class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <span>Restored your previous draft for this platform selection.</span>
      <div class="flex gap-2">
        <Button variant="ghost" size="sm" onclick={() => (draftDismissed = true)}>Keep</Button>
        <Button variant="outline" size="sm" onclick={discardDraft}>Start fresh</Button>
      </div>
    </Alert>
  {/if}

  {#if form?.success}
    <section
      bind:this={resultsAnchor}
      class="surface-card mb-10 rounded-xl border-primary/20 p-4 sm:p-6"
    >
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 class="font-heading text-xl font-bold text-collaboratory-navy">Platform answers</h2>
          <p class="mt-1 text-sm text-card-muted-foreground">
            Review the legal summary, open each platform form, then copy answers one at a time below.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <form
            method="POST"
            use:enhance={() => {
              generating = true;
              return async ({ result, update }) => {
                await update({ reset: false });
                generating = false;
              };
            }}
          >
            {#each Object.entries(submitValues) as [key, val] (key)}
              <input type="hidden" name={key} value={val ?? ""} />
            {/each}
            <Button type="submit" variant="secondary" disabled={generating}>
              {generating ? "Regenerating…" : "Regenerate answers"}
            </Button>
          </form>
          <Button variant="outline" onclick={toggleFormVisibility}>
            {showForm ? "Hide answers form" : "Edit answers"}
          </Button>
        </div>
      </div>
      <PlatformLegalNotice platforms={platformLegalInfo} />
      <ResultViewer results={form.by_vlopse} platforms={data.platforms} />
    </section>
  {/if}

  {#if showForm && !form?.success}
    <FormProgress
      class="mb-6"
      value={progressFilled}
      max={progressTotal}
      detail={progressDetail}
    />
  {/if}

  {#if showForm}
    <div bind:this={formAnchor} class="scroll-mt-6">
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div class="surface-panel inline-flex rounded-lg p-1 text-sm">
        <button
          type="button"
          class="rounded-md px-3 py-1.5 {viewMode === 'wizard'
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground'}"
          onclick={() => setViewMode("wizard")}
        >
          Step by step
        </button>
        <button
          type="button"
          class="rounded-md px-3 py-1.5 {viewMode === 'sections'
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground'}"
          onclick={() => setViewMode("sections")}
        >
          All sections
        </button>
      </div>
      {#if viewMode === "wizard" && groupedSections.length > 0}
        <p class="text-sm text-muted-foreground lg:hidden">
          {#if isReviewStep}
            Review & generate
          {:else}
            Step {wizardStep + 1} of {groupedSections.length}: {activeWizardSection?.section.label}
          {/if}
        </p>
      {/if}
    </div>

    <div class="grid gap-6 lg:grid-cols-[minmax(11rem,14rem)_minmax(0,1fr)] lg:gap-10">
      <aside class="lg:sticky lg:top-6 lg:self-start">
        <FormSectionNav
          sections={sectionStats}
          activeSectionId={viewMode === "wizard" ? activeSectionId : null}
          showReview={viewMode === "wizard"}
          reviewActive={isReviewStep}
          reviewReady={readiness.ready}
          onSelect={scrollToSection}
          onReviewSelect={goToReviewStep}
        />
      </aside>

      <div class="min-w-0">
    <form
      method="POST"
      use:enhance={() => {
        generating = true;
        return async ({ result, update }) => {
          try {
            await update({ reset: false });
            if (result.type === "failure") {
              toasts.show("Please fix the highlighted fields and try again.");
            } else if (result.type === "error") {
              toasts.show("Could not generate platform answers. Please try again.");
            }
          } finally {
            generating = false;
          }
        };
      }}
      enctype="multipart/form-data"
      class="flex flex-col gap-4"
    >
      <div class="hidden" aria-hidden="true">
        {#each data.questions as question (question.id)}
          {#if question.input_type !== "file_upload"}
            <input type="hidden" name={question.id} value={submitValues[question.id] ?? ""} />
          {/if}
        {/each}
      </div>
      {#if viewMode === "wizard"}
        {#if isReviewStep}
          <section class="surface-card rounded-xl p-4 sm:p-6">
            <h2 class="font-heading text-lg font-bold text-collaboratory-navy">Review your answers</h2>
            <p class="mt-1 text-sm text-muted-foreground">
              Check section progress before generating platform answers.
            </p>
            <ul class="mt-4 space-y-2 text-sm">
              {#each sectionStats as stat (stat.id)}
                <li class="flex items-center justify-between gap-3">
                  <span>{stat.label}</span>
                  <span class="text-muted-foreground">
                    {#if stat.requiredTotal > 0}
                      {stat.requiredFilled} / {stat.requiredTotal} required
                      <span class="text-muted-foreground/70"> · </span>
                    {/if}
                    {stat.filled} / {stat.total} fields
                    {#if stat.errorCount > 0}
                      <span class="text-destructive"> · {stat.errorCount} issue(s)</span>
                    {/if}
                  </span>
                </li>
              {/each}
            </ul>
          </section>
        {:else if activeWizardSection}
          {@const { section, rows } = activeWizardSection}
          <FormSection
            id="section-{section.id}"
            label={section.label}
            stats={sectionStats.find((entry) => entry.id === section.id)}
            flat={true}
            open={true}
            onOpenChange={() => {}}
          >
            {#snippet children()}
              {#each rows as row (row.kind === "single" ? row.question.id : row.baseId)}
                <div
                  data-question-id={row.kind === "single" ? row.question.id : row.variants[0]?.id}
                >
                  {#if row.kind === "platform_group"}
                    <PlatformScopedGroup
                      label={row.label}
                      required={row.required}
                      visible={row.variants.some(
                        (variant) => visibility[variant.id] || variant.required,
                      )}
                      variants={row.variants.map(variantProps)}
                      bind:values
                      formValues={expandFormValues(values)}
                      conditions={data.conditions}
                      platforms={data.platforms}
                    />
                  {:else}
                    {@const structured = isStructuredQuestion(row.question.input_type)}
                    <Question
                      id={row.question.id}
                      text={structured ? "" : row.question.text}
                      required={row.question.required ?? false}
                      visible={visibility[row.question.id] ?? true}
                      bind:value={values[row.question.id]}
                      input_type={row.question.input_type}
                      help_text={row.question.help_text}
                      config={row.question.config}
                      options={row.question.options}
                      formValues={expandFormValues(values)}
                      conditions={data.conditions}
                      platforms={data.platforms}
                      embedded={structured}
                      requiredFieldIds={requiredContext.requiredFieldIds}
                      validation={form?.validation_errors?.find(
                        (item) => item.question_id == row.question.id,
                      )?.description}
                    />
                  {/if}
                </div>
              {/each}
            {/snippet}
          </FormSection>
        {/if}

        <div class="surface-card flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-4 sm:px-6">
          <Button
            type="button"
            variant="outline"
            disabled={wizardStep === 0}
            onclick={() => (wizardStep = Math.max(0, wizardStep - 1))}
          >
            Back
          </Button>
          {#if !isReviewStep}
            <Button
              type="button"
              class="btn-collaboratory"
              onclick={() =>
                (wizardStep = Math.min(groupedSections.length, wizardStep + 1))}
            >
              {wizardStep >= groupedSections.length - 1 ? "Review" : "Next"}
            </Button>
          {:else}
            <Button
              type="submit"
              size="lg"
              class="btn-collaboratory"
              disabled={generating || !readiness.ready}
            >
              {generating ? "Generating…" : "Generate platform answers"}
            </Button>
          {/if}
        </div>
      {:else}
        {#each groupedSections as { section, rows } (section.id)}
          <FormSection
            id="section-{section.id}"
            label={section.label}
            stats={sectionStats.find((entry) => entry.id === section.id)}
            open={sectionOpen[section.id] ?? true}
            onOpenChange={(value) => {
              sectionOpen = { ...sectionOpen, [section.id]: value };
            }}
          >
            {#snippet children()}
              {#each rows as row (row.kind === "single" ? row.question.id : row.baseId)}
                <div
                  data-question-id={row.kind === "single" ? row.question.id : row.variants[0]?.id}
                >
                  {#if row.kind === "platform_group"}
                    <PlatformScopedGroup
                      label={row.label}
                      required={row.required}
                      visible={row.variants.some(
                        (variant) => visibility[variant.id] || variant.required,
                      )}
                      variants={row.variants.map(variantProps)}
                      bind:values
                      formValues={expandFormValues(values)}
                      conditions={data.conditions}
                      platforms={data.platforms}
                    />
                  {:else}
                    {@const structured = isStructuredQuestion(row.question.input_type)}
                    <Question
                      id={row.question.id}
                      text={structured ? "" : row.question.text}
                      required={row.question.required ?? false}
                      visible={visibility[row.question.id] ?? true}
                      bind:value={values[row.question.id]}
                      input_type={row.question.input_type}
                      help_text={row.question.help_text}
                      config={row.question.config}
                      options={row.question.options}
                      formValues={expandFormValues(values)}
                      conditions={data.conditions}
                      platforms={data.platforms}
                      embedded={structured}
                      requiredFieldIds={requiredContext.requiredFieldIds}
                      validation={form?.validation_errors?.find(
                        (item) => item.question_id == row.question.id,
                      )?.description}
                    />
                  {/if}
                </div>
              {/each}
            {/snippet}
          </FormSection>
        {/each}

        <div class="surface-card rounded-xl px-4 py-4 sm:px-6">
          {#if !readiness.ready}
            <div class="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-3 text-sm">
              <p class="font-medium text-card-foreground">
                {readiness.missing.length} required field{readiness.missing.length === 1
                  ? ""
                  : "s"} still empty
              </p>
              <ul class="mt-2 space-y-1 text-muted-foreground">
                {#each readiness.missing.slice(0, 6) as field (field.questionId)}
                  <li>
                    <button
                      type="button"
                      class="text-left hover:text-card-foreground"
                      onclick={() => scrollToSection(field.sectionId)}
                    >
                      {field.label}
                      <span class="text-xs">
                        ({sectionLabelById[field.sectionId] ?? field.sectionId})
                      </span>
                    </button>
                  </li>
                {/each}
                {#if readiness.missing.length > 6}
                  <li>…and {readiness.missing.length - 6} more</li>
                {/if}
              </ul>
            </div>
          {/if}
          <div class="flex items-center justify-end gap-4">
            <Button
              type="submit"
              size="lg"
              class="btn-collaboratory"
              disabled={generating || !readiness.ready}
            >
              {generating ? "Generating…" : "Generate platform answers"}
            </Button>
          </div>
        </div>
      {/if}
    </form>

    {#if form?.validation_errors?.length}
      <p
        class="mt-6 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
      >
        Please fix the highlighted fields and try again.
      </p>
    {/if}
      </div>
    </div>
    </div>
  {/if}

  {#if form?.transformation_errors}
    <div class="mt-8">
      <TransformationErrorPanel
        errors={form.transformation_errors}
        mappingIndex={data.mappingIndex}
        {questionById}
        onEdit={openFormForEditing}
      />
    </div>
  {/if}
</div>

<ConfirmDialog
  bind:open={changePlatformsOpen}
  title="Change platforms?"
  description="Your answers are saved in this browser. Overlapping fields will be kept when you pick new platforms."
  confirmLabel="Change platforms"
  onConfirm={confirmChangePlatforms}
/>
