<script lang="ts">
  import {
    FAIRER_TERMS_REPORT_URL,
    type PlatformLegalInfo,
    platformsWithLegalContent,
  } from "$lib/platformLegal";

  type Props = {
    platforms: PlatformLegalInfo[];
  };

  let { platforms }: Props = $props();

  const visible = $derived(platformsWithLegalContent(platforms));
</script>

{#if visible.length > 0}
  <section
    class="mb-6 rounded-xl border border-amber-500/35 border-l-4 border-l-amber-500 bg-field-bg p-4 sm:p-5"
    aria-labelledby="platform-legal-notice-heading"
  >
    <div>
      <h2 id="platform-legal-notice-heading" class="font-heading text-lg font-bold text-collaboratory-navy">
        Before you open platform forms
      </h2>
      <p class="mt-1 text-sm text-card-foreground">
        Each platform will ask you to accept separate legal agreements. These go beyond what
        DSA Article 40(12) requires. Review the documents and implications below before
        leaving this helper.
      </p>
    </div>

    <div class="mt-5 space-y-4">
      {#each visible as platform (platform.id)}
        <div class="surface-card rounded-lg p-4">
          <h3 class="font-heading font-bold text-collaboratory-navy">{platform.name}</h3>

          {#if platform.disclaimers.length > 0}
            <div class="mt-3">
              <p class="text-xs font-medium uppercase tracking-wide text-field-hint">
                Agreements you may be asked to accept
              </p>
              <ul class="mt-2 space-y-3">
                {#each platform.disclaimers as disclaimer (disclaimer.id)}
                  <li class="text-sm leading-relaxed text-card-foreground">
                    <p>{disclaimer.text}</p>
                    {#if disclaimer.highlights && disclaimer.highlights.length > 0}
                      <p class="mt-1 text-xs text-field-hint">
                        Key terms:
                        {disclaimer.highlights.join(" · ")}
                      </p>
                    {/if}
                    {#if disclaimer.links && disclaimer.links.length > 0}
                      <ul class="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                        {#each disclaimer.links as link (link.url)}
                          <li>
                            <a
                              href={link.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              class="link-on-card"
                            >
                              {link.label}
                            </a>
                          </li>
                        {/each}
                      </ul>
                    {/if}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if platform.termImplications.length > 0}
            <div class="mt-4">
              <p class="text-xs font-medium uppercase tracking-wide text-field-hint">
                What signing typically entails
              </p>
              <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-card-foreground">
                {#each platform.termImplications as implication, i (`${platform.id}-${i}`)}
                  <li>{implication}</li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <p class="mt-4 text-xs text-card-muted-foreground">
      Independent analysis:
      <a
        href={FAIRER_TERMS_REPORT_URL}
        target="_blank"
        rel="noopener noreferrer"
        class="link-on-card"
      >
        Mozilla Foundation — Fairer Terms for Data Access (PDF)
      </a>
      . This helper supports your access application but does not provide legal advice.
    </p>
  </section>
{/if}
