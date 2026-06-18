<script lang="ts">
  import type { InputType, DsaQuestion } from "@api/types.gen";
  import Question from "$lib/Question.svelte";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import type { ConditionsMap } from "$lib/conditions";

  type PlatformRef = { id: string; name: string };

  type Variant = {
    id: string;
    text: string;
    required: boolean;
    visible: boolean;
    input_type: InputType;
    help_text?: string | null;
    config?: DsaQuestion["config"];
    options?: string[] | null;
    vlopse?: string | null;
    validation?: string | string[] | null;
  };

  type Props = {
    label: string;
    required: boolean;
    visible: boolean;
    variants: Variant[];
    values?: Record<string, string | undefined>;
    platforms?: PlatformRef[];
    conditions?: ConditionsMap;
    formValues?: Record<string, string | undefined>;
  };

  let {
    label,
    required,
    visible,
    variants,
    values = $bindable({}),
    platforms = [],
    conditions = {},
    formValues = {},
  }: Props = $props();

  let activeVlopse = $state("");

  const visibleVariants = $derived(variants.filter((variant) => variant.visible || variant.required));

  $effect(() => {
    if (!visibleVariants.length) return;
    if (!visibleVariants.some((variant) => variant.vlopse === activeVlopse)) {
      activeVlopse = visibleVariants[0]?.vlopse ?? "";
    }
  });

  function platformLabel(vlopseId: string): string {
    return platforms.find((platform) => platform.id === vlopseId)?.name ?? vlopseId;
  }

  const hidden = $derived(!required && !visible);
</script>

{#if !hidden}
  <fieldset class="py-5">
    <legend class="font-heading text-base font-bold leading-snug text-card-foreground">
      {label}
      <Badge variant={required ? "required" : "secondary"} class="ml-1.5">
        {required ? "Required" : "Optional"}
      </Badge>
    </legend>

    {#if visibleVariants.length > 1}
      <div class="platform-tabs mt-3" role="tablist" aria-label="{label} platforms">
        {#each visibleVariants as variant (variant.id)}
          {#if variant.vlopse}
            <button
              type="button"
              role="tab"
              aria-selected={activeVlopse === variant.vlopse}
              class:platform-tab-active={activeVlopse === variant.vlopse}
              class="platform-tab"
              onclick={() => {
                activeVlopse = variant.vlopse ?? "";
              }}
            >
              {platformLabel(variant.vlopse)}
            </button>
          {/if}
        {/each}
      </div>
    {/if}

    {#each visibleVariants as variant (variant.id)}
      {#if visibleVariants.length === 1 || variant.vlopse === activeVlopse}
        <div class="mt-3" role="tabpanel">
          <Question
            id={variant.id}
            text={variant.text}
            required={variant.required}
            visible={variant.visible}
            input_type={variant.input_type}
            help_text={variant.help_text}
            config={variant.config}
            options={variant.options}
            bind:value={values[variant.id]}
            validation={variant.validation}
            {formValues}
            {conditions}
            {platforms}
            embedded
          />
        </div>
      {/if}
    {/each}
  </fieldset>
{/if}
