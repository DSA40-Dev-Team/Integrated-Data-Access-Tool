<script lang="ts">
  import SchemaFieldInput from "$lib/SchemaFieldInput.svelte";
  import {
    buildOrgOptions,
    type OrgOption,
    type SchemaField,
    PRIMARY_ORG_ID,
  } from "$lib/structured";

  type Props = {
    affiliations: Record<string, unknown>[];
    orgOptions: OrgOption[];
    affiliationFields: SchemaField[];
    itemLabel?: string;
    onupdate?: (affiliations: Record<string, unknown>[]) => void;
  };

  let {
    affiliations = $bindable([]),
    orgOptions,
    affiliationFields,
    itemLabel = "Affiliation",
    onupdate,
  }: Props = $props();

  function notify() {
    onupdate?.(affiliations);
  }

  function addAffiliation() {
    const defaultOrg = orgOptions[0]?.id ?? PRIMARY_ORG_ID;
    affiliations = [
      ...affiliations,
      {
        organisation_id: defaultOrg,
        "org-role": "",
        "org-department": "",
        "org-evidence": "",
      },
    ];
    notify();
  }

  function removeAffiliation(index: number) {
    affiliations = affiliations.filter((_, i) => i !== index);
    notify();
  }

  function setAffField(index: number, fieldId: string, value: string) {
    affiliations = affiliations.map((aff, i) =>
      i === index ? { ...aff, [fieldId]: value } : aff,
    );
    notify();
  }
</script>

<div class="affiliations">
  {#each affiliations as aff, affIndex (affIndex)}
    <div class="affiliation-card">
      <div class="affiliation-head">
        <strong>{itemLabel} {affIndex + 1}</strong>
        {#if affiliations.length > 1}
          <button type="button" class="link-btn" onclick={() => removeAffiliation(affIndex)}>
            Remove
          </button>
        {/if}
      </div>

      <label class="field-label" for={`aff-org-${affIndex}`}>Organisation</label>
      <select
        id={`aff-org-${affIndex}`}
        class="native-select"
        value={String(aff.organisation_id ?? PRIMARY_ORG_ID)}
        onchange={(e) =>
          setAffField(affIndex, "organisation_id", e.currentTarget.value)}
      >
        {#each orgOptions as opt (opt.id)}
          <option value={opt.id}>{opt.label}</option>
        {/each}
      </select>

      {#each affiliationFields.filter((f) => f.id !== "organisation_id") as field (field.id)}
        <label class="field-label" for={`aff-${affIndex}-${field.id}`}>{field.text_en}</label>
        <SchemaFieldInput
          id={`aff-${affIndex}-${field.id}`}
          {field}
          value={String(aff[field.id] ?? "")}
          onchange={(v) => setAffField(affIndex, field.id, v)}
        />
      {/each}
    </div>
  {/each}

  <button type="button" class="add-btn" onclick={addAffiliation}>+ Add {itemLabel.toLowerCase()}</button>
</div>

<style>
  .affiliations {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .affiliation-card {
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 0.5rem;
    padding: 0.75rem;
    background: color-mix(in srgb, var(--muted, #f4f4f5) 35%, transparent);
  }
  .affiliation-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }
  .field-label {
    display: block;
    font-size: 0.8125rem;
    margin-top: 0.5rem;
    margin-bottom: 0.25rem;
    color: var(--muted-foreground, #6b7280);
  }
  .native-select {
    width: 100%;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 0.375rem;
    padding: 0.5rem 0.75rem;
    background: var(--background, #fff);
  }
  .add-btn,
  .link-btn {
    font-size: 0.875rem;
    color: var(--primary, #2563eb);
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
  }
  .add-btn {
    align-self: flex-start;
    margin-top: 0.25rem;
  }
</style>
