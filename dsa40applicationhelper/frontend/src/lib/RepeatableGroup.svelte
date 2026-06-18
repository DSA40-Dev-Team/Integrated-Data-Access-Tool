<script lang="ts">
  import { onMount } from "svelte";
  import AffiliationEditor from "$lib/AffiliationEditor.svelte";
  import SchemaFieldInput from "$lib/SchemaFieldInput.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import { isVisible, type ConditionsMap } from "$lib/conditions";
  import {
    buildOrgOptions,
    nextOrgId,
    parseItems,
    serializeItems,
    type FieldSchema,
    type SchemaField,
    PRIMARY_ORG_ID,
  } from "$lib/structured";

  type Props = {
    id: string;
    config?: Record<string, unknown> | null;
    formValues?: Record<string, string | undefined>;
    conditions?: ConditionsMap;
    value?: string;
    validation?: string | string[] | null;
  };

  let {
    id,
    config = null,
    formValues = {},
    conditions = {},
    value = $bindable("[]"),
    validation = null,
  }: Props = $props();

  let schemaData = $state<FieldSchema | null>(null);
  let items = $state<Record<string, unknown>[]>([]);
  let personFields = $state<SchemaField[]>([]);
  let affiliationFields = $state<SchemaField[]>([]);
  let schemaFields = $state<SchemaField[]>([]);

  const schemaName = $derived(String(config?.schema ?? ""));
  const itemLabel = $derived(String(config?.item_label ?? "Item"));
  const isTeamMember = $derived(schemaName === "team-member");
  const isOrganisation = $derived(schemaName === "organisation-profile");

  const orgOptions = $derived(
    buildOrgOptions(String(formValues["team-organisations"] ?? "[]"), formValues),
  );

  const validationErrors = $derived(
    Array.isArray(validation) ? validation : validation ? [validation] : [],
  );

  const canModify = $derived(
    isVisible(id, conditions, formValues) &&
      (id !== "collab-researchers" && id !== "team-organisations"
        ? true
        : formValues["collab-binary"] === "Yes"),
  );

  function syncOut() {
    value = serializeItems(items);
  }

  function loadFromValue() {
    items = parseItems(value);
  }

  function blankEntry(): Record<string, unknown> {
    if (isOrganisation) return { id: nextOrgId(items) };
    if (isTeamMember) {
      return {
        person: Object.fromEntries(personFields.map((f) => [f.id, ""])),
        affiliations: [
          {
            organisation_id: orgOptions[0]?.id ?? PRIMARY_ORG_ID,
            "org-role": "",
            "org-department": "",
            "org-evidence": "",
          },
        ],
      };
    }
    return Object.fromEntries(schemaFields.map((field) => [field.id, ""]));
  }

  onMount(async () => {
    loadFromValue();
    if (!schemaName) return;
    const res = await fetch(`/api/schemas/${schemaName}`);
    if (!res.ok) return;
    schemaData = (await res.json()) as FieldSchema;
    schemaFields = schemaData.fields;

    if (isTeamMember) {
      const [personRes, affRes] = await Promise.all([
        fetch(`/api/schemas/person-profile`),
        fetch(`/api/schemas/affiliation-profile`),
      ]);
      if (personRes.ok) {
        personFields = ((await personRes.json()) as FieldSchema).fields;
      }
      if (affRes.ok) {
        affiliationFields = ((await affRes.json()) as FieldSchema).fields;
      }
    }
  });

  $effect(() => {
    if (!items.length && value && value !== "[]") {
      loadFromValue();
    }
  });

  function addItem() {
    items = [...items, blankEntry()];
    syncOut();
  }

  function removeItem(index: number) {
    items = items.filter((_, i) => i !== index);
    syncOut();
  }

  function setOrgField(index: number, fieldId: string, fieldValue: string) {
    items = items.map((item, i) =>
      i === index ? { ...item, [fieldId]: fieldValue } : item,
    );
    syncOut();
  }

  function setPersonField(index: number, fieldId: string, fieldValue: string) {
    items = items.map((item, i) => {
      if (i !== index) return item;
      const person = (item.person as Record<string, unknown>) ?? {};
      return { ...item, person: { ...person, [fieldId]: fieldValue } };
    });
    syncOut();
  }

  function setAffiliations(index: number, affiliations: Record<string, unknown>[]) {
    items = items.map((item, i) =>
      i === index ? { ...item, affiliations } : item,
    );
    syncOut();
  }
</script>


<div class="flex flex-col gap-3">
  {#if items.length === 0}
    <p
      class="m-0 rounded-lg border border-dashed border-field-border bg-card-muted/60 p-4 text-sm text-card-muted-foreground"
    >
      No {itemLabel.toLowerCase()} added yet. Use the button below when you need to include one.
    </p>
  {/if}

  {#each items as item, itemIndex (itemIndex)}
    <details class="rounded-lg border border-field-border bg-card-muted/40" open>
      <summary
        class="flex cursor-pointer list-none items-center justify-between px-4 py-3.5 [&::-webkit-details-marker]:hidden"
      >
        <span class="text-sm font-semibold">{itemLabel} {itemIndex + 1}</span>
        <button
          type="button"
          class="cursor-pointer border-0 bg-transparent p-0 text-sm text-primary hover:underline"
          onclick={(event) => {
            event.preventDefault();
            removeItem(itemIndex);
          }}
        >
          Remove
        </button>
      </summary>

      <div class="px-4 pb-4">
        {#if isOrganisation || (!isTeamMember && schemaFields.length > 0)}
          {#each schemaFields as field (field.id)}
            <label
              class="mb-1 mt-2 block text-[0.8125rem] text-muted-foreground"
              for={`${id}-${itemIndex}-${field.id}`}
            >
              {field.text_en}
            </label>
            <SchemaFieldInput
              id={`${id}-${itemIndex}-${field.id}`}
              {field}
              value={String(item[field.id] ?? "")}
              onchange={(v) => setOrgField(itemIndex, field.id, v)}
            />
          {/each}
        {:else if isTeamMember}
          <p class="mb-1 mt-3 text-sm font-semibold">Person</p>
          {#each personFields as field (field.id)}
            <label
              class="mb-1 mt-2 block text-[0.8125rem] text-muted-foreground"
              for={`${id}-${itemIndex}-person-${field.id}`}
            >
              {field.text_en}
            </label>
            <SchemaFieldInput
              id={`${id}-${itemIndex}-person-${field.id}`}
              {field}
              value={String((item.person as Record<string, unknown> | undefined)?.[field.id] ?? "")}
              onchange={(v) => setPersonField(itemIndex, field.id, v)}
            />
          {/each}

          <p class="mb-1 mt-3 text-sm font-semibold">Affiliations</p>
          <AffiliationEditor
            affiliations={(item.affiliations as Record<string, unknown>[]) ?? []}
            {orgOptions}
            {affiliationFields}
            onupdate={(affs) => setAffiliations(itemIndex, affs)}
          />
        {/if}
      </div>
    </details>
  {/each}

  <Button
    type="button"
    variant="outline"
    size="sm"
    class="self-start"
    disabled={!canModify}
    onclick={addItem}
  >
    + Add {itemLabel.toLowerCase()}
  </Button>

  {#if validationErrors.length > 0}
    <ul class="mt-1 list-none p-0 text-sm text-destructive" role="alert">
      {#each validationErrors as err}
        <li>{err}</li>
      {/each}
    </ul>
  {/if}
</div>
