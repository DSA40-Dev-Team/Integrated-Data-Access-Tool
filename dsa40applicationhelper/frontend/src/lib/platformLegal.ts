export type PlatformDisclaimerLink = {
  label: string;
  url: string;
};

export type PlatformDisclaimer = {
  id: string;
  text: string;
  highlights?: string[];
  links?: PlatformDisclaimerLink[];
};

export type PlatformLegalInfo = {
  id: string;
  name: string;
  applicationLink?: string;
  modality?: string;
  disclaimers: PlatformDisclaimer[];
  termImplications: string[];
};

export const FAIRER_TERMS_REPORT_URL =
  "https://assets.mofoprod.net/network/documents/Fairer_Terms_for_Data_Access.pdf";

export function hasLegalContent(platform: PlatformLegalInfo): boolean {
  return platform.disclaimers.length > 0 || platform.termImplications.length > 0;
}

export function platformsWithLegalContent(platforms: PlatformLegalInfo[]): PlatformLegalInfo[] {
  return platforms.filter(hasLegalContent);
}
