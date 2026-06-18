<script lang="ts">
  import { Input } from "$lib/components/ui/input";

  type Props = {
    id: string;
    name?: string;
    value?: string;
    options: string[];
    placeholder?: string;
    onchange?: (value: string) => void;
  };

  let {
    id,
    value = $bindable(""),
    options,
    placeholder = "Search for a country…",
    onchange,
  }: Props = $props();

  let query = $state("");
  let open = $state(false);
  let listId = $derived(`${id}-country-list`);

  $effect(() => {
    query = value;
  });

  const filtered = $derived(
    options
      .filter((option) => option.toLowerCase().includes(query.trim().toLowerCase()))
      .slice(0, 80),
  );

  function commit(next: string) {
    value = next;
    query = next;
    open = false;
    onchange?.(next);
  }

  function handleInput(next: string) {
    query = next;
    value = next;
    open = true;
    onchange?.(next);
  }
</script>

<div class="country-combobox">
  <Input
    {id}
    type="text"
    role="combobox"
    aria-expanded={open}
    aria-controls={listId}
    autocomplete="off"
    {placeholder}
    bind:value={query}
    class="w-full"
    oninput={(e) => handleInput(e.currentTarget.value)}
    onfocus={() => (open = true)}
    onblur={() => {
      setTimeout(() => {
        open = false;
      }, 150);
    }}
  />
  {#if open && filtered.length > 0}
    <ul id={listId} class="country-list" role="listbox">
      {#each filtered as option (option)}
        <li>
          <button
            type="button"
            role="option"
            aria-selected={option === value}
            class="country-option"
            onmousedown={(e) => e.preventDefault()}
            onclick={() => commit(option)}
          >
            {option}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .country-combobox {
    position: relative;
    width: 100%;
  }
  .country-list {
    position: absolute;
    z-index: 20;
    top: calc(100% + 0.25rem);
    left: 0;
    right: 0;
    max-height: 14rem;
    overflow-y: auto;
    margin: 0;
    padding: 0.25rem;
    list-style: none;
    border: 1px solid var(--field-border);
    border-radius: 0.375rem;
    background: #ffffff;
    box-shadow: 0 4px 12px rgb(0 0 0 / 0.12);
  }
  .country-option {
    display: block;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    padding: 0.375rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    color: var(--collaboratory-text);
    cursor: pointer;
  }
  .country-option:hover,
  .country-option[aria-selected="true"] {
    background: var(--card-muted);
  }
</style>
