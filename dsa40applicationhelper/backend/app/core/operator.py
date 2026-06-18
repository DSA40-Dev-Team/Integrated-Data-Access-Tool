from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pycountry import countries
from typing_extensions import override

from app.core.models import PlatformMapping, PlatformMappingComplex

Inputs = str | list[str] | None


@dataclass(frozen=True)
class OperatorSpec:
    name: str
    label: str
    input_arity: Literal["single", "list", "any"]
    description: str = ""
    needs_context: bool = False
    constant_output: bool = False


class OperatorExecutionError(Exception):
    def __init__(self, message: str, inputs: Inputs) -> None:
        if isinstance(inputs, list):
            list_inputs = inputs
        else:
            list_inputs = [inputs]
        super().__init__({"message": message, "inputs": list_inputs})


class AbstractOperator(ABC):
    needs_context: bool = False

    @abstractmethod
    def _apply(self, inputs: Inputs) -> str: ...

    def apply(self, inputs: Inputs, answer_map: dict[str, str | None] | None = None):
        try:
            if self.needs_context and answer_map is not None:
                result = self._apply_with_context(inputs, answer_map)
            else:
                result = self._apply(inputs)
            return result
        except TypeError as e:
            message = e.args[0]
            raise OperatorExecutionError(message, inputs) from None

        except ValueError as e:
            message = e.args[0]
            raise OperatorExecutionError(message, inputs) from None

    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        return self._apply(inputs)


class MakeISOOperator(AbstractOperator):
    @override
    def _apply(self, inputs: Inputs):
        if inputs is None:
            raise TypeError("Cannot create ISO from None argument.")
        if isinstance(inputs, list):
            raise TypeError("Cannot create ISO from list argument.")
        result = countries.get(name=inputs)
        if not result:
            raise ValueError(f"Unknown country {inputs}")
        return result.alpha_3


class JoinOperator(AbstractOperator):
    delimiter: str

    def __init__(self, delimiter: str):
        self.delimiter = delimiter

    @override
    def _apply(self, inputs: Inputs):
        if inputs is None:
            raise TypeError("Cannot join None type")
        if isinstance(inputs, str):
            raise TypeError("Cannot join str type")
        return self.delimiter.join(inputs)


class NoopOperator(AbstractOperator):
    @override
    def _apply(self, inputs: Inputs):
        if isinstance(inputs, list):
            raise TypeError("Cannot transform lists")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return inputs


class LiteralValueOperator(AbstractOperator):
    """Emit a fixed platform answer without user input."""

    constant_output = True

    def __init__(self, value: str) -> None:
        self._value = value

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._value


class JoinParagraphOperator(AbstractOperator):
    """Join multiple text answers into one platform field (e.g. combined research description)."""

    @override
    def _apply(self, inputs: Inputs):
        if not isinstance(inputs, list):
            raise TypeError("Expected a list of text values")
        parts = [part.strip() for part in inputs if part and str(part).strip()]
        if not parts:
            raise ValueError("No text values to combine")
        return "\n\n".join(parts)


class JoinDateRangeOperator(AbstractOperator):
    """Format two dates as a single access timeframe string (free-form platform fields)."""

    @override
    def _apply(self, inputs: Inputs):
        if not isinstance(inputs, list) or len(inputs) != 2:
            raise TypeError("Expected exactly two date values")
        start, end = (str(v).strip() for v in inputs)
        if not start or not end:
            raise ValueError("Both start and end dates are required")
        return f"{start} to {end}"


def _parse_date(value: str) -> datetime:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value}")


def _duration_bucket(days: int) -> str:
    if days <= 1:
        return "24 hours"
    if days <= 7:
        return "1 - 7 days"
    if days <= 28:
        return "1 - 4 weeks"
    if days <= 90:
        return "30 - 90 days"
    if days <= 365:
        return "3 - 12 months"
    return ">12 months"


class MakeDurationOperator(AbstractOperator):
    """Map a storage/access date range to a duration bucket (e.g. YouTube Y19)."""

    @override
    def _apply(self, inputs: Inputs):
        if not isinstance(inputs, list) or len(inputs) != 2:
            raise TypeError("Expected exactly two date values")
        start = _parse_date(str(inputs[0]))
        end = _parse_date(str(inputs[1]))
        if end < start:
            raise ValueError("End date must not be before start date")
        days = (end - start).days
        return _duration_bucket(days)


class MakeReportOperator(AbstractOperator):
    """Alias for joining narrative sections (summary + systemic risk, etc.)."""

    def __init__(self) -> None:
        self._join = JoinParagraphOperator()

    @override
    def _apply(self, inputs: Inputs):
        return self._join._apply(inputs)

class AppleMakeDurationOperator(AbstractOperator):
    """Apple: research duration as a prose sentence."""

    @override
    def _apply(self, inputs: Inputs):
        if not isinstance(inputs, list) or len(inputs) != 2:
            raise TypeError("Expected exactly two date values")
        start, end = (str(v).strip() for v in inputs)
        if not start or not end:
            raise ValueError("Both start and end dates are required")
        return (
            f"The research project is supposed to run from {start} to {end}."
        )


class AppleCollabSentenceOperator(AbstractOperator):
    """Apple: collaboration yes/no → full-sentence confirmation."""

    @override
    def _apply(self, inputs: Inputs):
        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        value = str(inputs).strip().lower()
        if value == "yes":
            return "I am collaborating on this project."
        if value == "no":
            return "I'm making this request as an individual researcher"
        raise ValueError(f"Expected Yes or No, got: {inputs}")


class FormatTeamResearchersOperator(AbstractOperator):
    """Format structured collab-researchers JSON into platform text."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.team_research import format_team_researchers

        if isinstance(inputs, list):
            raise TypeError("Expected a single structured answer value")
        if inputs is None or not str(inputs).strip():
            raise ValueError("No team researchers provided")
        return format_team_researchers(str(inputs), answer_map)


class AppleTeamResearchersOperator(FormatTeamResearchersOperator):
    """Apple A4: same structured formatting as the generic team formatter."""

    pass


class MetaCollabEmailsOperator(AbstractOperator):
    """Meta M27: comma-separated emails from collab-researchers when collab-binary is Yes."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.team_research import format_collab_emails

        if isinstance(inputs, list):
            raise TypeError("Expected a single structured answer value")
        if inputs is None:
            return ""
        return format_collab_emails(str(inputs), answer_map)


class MetaMclResearchToolsOperator(AbstractOperator):
    """Meta M23: MCL web tool fixed; optional API access from platform-specific answer."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.team_research import format_meta_mcl_research_tools

        return format_meta_mcl_research_tools(answer_map)


class AppleAffiliationDemonstrationOperator(AbstractOperator):
    """Apple A5: organisation identity, contact details, and affiliation proof."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.team_research import format_apple_affiliation_demonstration

        if isinstance(inputs, list):
            raise TypeError("Expected a single organisation name value")
        if inputs is None or not str(inputs).strip():
            raise TypeError("Cannot transform None")
        return format_apple_affiliation_demonstration(answer_map)


_PUBLICATION_NO_SENTENCE = "No, the research will not be published."


class ApplePublicationAnswerOperator(AbstractOperator):
    """Apple A9: Yes/No gate with publication details when Yes."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        value = str(inputs).strip().lower()
        if value == "no":
            return _PUBLICATION_NO_SENTENCE
        if value == "yes":
            publication = (answer_map.get("research-publication") or "").strip()
            if not publication:
                raise ValueError(
                    "Publication details are required when planning to publish"
                )
            return publication
        raise ValueError(f"Expected Yes or No, got: {inputs}")


class FormatFundingSummaryOperator(AbstractOperator):
    """Tier-1/3 funding summary from gate, structured entries, or free text."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_funding_summary

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_funding_summary(answer_map)


class FormatFundingSourcesTextOperator(AbstractOperator):
    """Funding-sources free text when funded; fixed phrase when not."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_funding_sources_text

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_funding_sources_text(answer_map)


class CommercialIndependenceAndOperator(AbstractOperator):
    """Pinterest P16: person AND org AND research commercial independence."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_commercial_independence_and

        return format_commercial_independence_and(answer_map)


class TiktokAffiliationTypeOperator(AbstractOperator):
    """TikTok T2: affiliation category from org-type."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.affiliation_format import format_tiktok_affiliation_type

        if isinstance(inputs, list):
            raise TypeError("Expected a single org-type value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_tiktok_affiliation_type(answer_map)


class FormatOrgAffiliationOperator(AbstractOperator):
    """X X4: organisation affiliation summary."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.affiliation_format import format_org_affiliation_summary

        return format_org_affiliation_summary(answer_map)


class XCommercialInterestsOperator(AbstractOperator):
    """X X6: organisational independence and evidence."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.affiliation_format import format_x_commercial_interests

        return format_x_commercial_interests(answer_map)


class AppleFundingDisclosureOperator(AbstractOperator):
    """Apple A17: funding sources, model, amounts, and terms."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_apple_funding_disclosure

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_apple_funding_disclosure(answer_map)


class AppleFundingBreakdownOperator(AbstractOperator):
    """Apple A18: percentage split across funding sources."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_apple_funding_breakdown

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_apple_funding_breakdown(answer_map)


class GoogleFundingSponsorTypesOperator(AbstractOperator):
    """Google G23: sponsor institution types."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_google_funding_sponsor_types

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_google_funding_sponsor_types(answer_map)


class GoogleFundingOrgNamesOperator(AbstractOperator):
    """Google G24: sponsoring organisation names."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_google_funding_org_names

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_google_funding_org_names(answer_map)


class GoogleFundingDisclosureOperator(AbstractOperator):
    """Google G27: per-source grant year, duration, and amount."""

    needs_context = True

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        from app.core.funding_format import format_google_funding_disclosure

        if isinstance(inputs, list):
            raise TypeError("Expected a single Yes/No value")
        if inputs is None:
            raise TypeError("Cannot transform None")
        return format_google_funding_disclosure(answer_map)


class _ContextSecurityOperator(AbstractOperator):
    """Base for security formatters that read the full answer map."""

    needs_context = True
    _formatter_name: str = ""

    @override
    def _apply(self, inputs: Inputs) -> str:
        return self._apply_with_context(inputs, {})

    @override
    def _apply_with_context(
        self, inputs: Inputs, answer_map: dict[str, str | None]
    ) -> str:
        import importlib

        module = importlib.import_module("app.core.security_format")
        formatter = getattr(module, self._formatter_name)
        if isinstance(inputs, list):
            if not any(str(v).strip() for v in inputs):
                raise TypeError("Expected at least one trigger value")
        elif inputs is None or not str(inputs).strip():
            raise TypeError("Cannot transform None")
        return formatter(answer_map)


class FormatTomSummaryOperator(_ContextSecurityOperator):
    _formatter_name = "format_tom_summary"


class GoogleDataProtectionOperator(_ContextSecurityOperator):
    _formatter_name = "format_google_data_protection"


class AppleRightsProtectionOperator(_ContextSecurityOperator):
    _formatter_name = "format_apple_rights_protection"


class ApplePurposeConfirmationOperator(_ContextSecurityOperator):
    _formatter_name = "format_apple_purpose_confirmation"


class AppleSecurityArrangementsOperator(_ContextSecurityOperator):
    _formatter_name = "format_apple_security_arrangements"


class ApplePurposeLimitationOperator(_ContextSecurityOperator):
    _formatter_name = "format_apple_purpose_limitation"


class PinterestPurposeGateOperator(_ContextSecurityOperator):
    _formatter_name = "format_pinterest_purpose_gate"


def hydrate_operator(operator: PlatformMapping):
    # FIXME: No-Op is simply a mapping. So we don't really want this here? or it's more elegant, let's see
    if isinstance(operator, str):
        print(f"DEBUG no-op {operator}")

        return NoopOperator()
    if isinstance(operator, PlatformMappingComplex):
        match operator.operation:
            case "literal-yes":
                return LiteralValueOperator("Yes")
            case "literal-no":
                return LiteralValueOperator("No")
            case "literal-value":
                if not operator.value:
                    raise ValueError("literal-value requires a value")
                return LiteralValueOperator(operator.value)
    match operator.operation:
        case "make-iso":
            return MakeISOOperator()
        case "join-space":
            return JoinOperator(" ")
        case "join-comma":
            return JoinOperator(", ")
        case "join-paragraph":
            return JoinParagraphOperator()
        case "join-date-range":
            return JoinDateRangeOperator()
        case "make-duration":
            return MakeDurationOperator()
        case "make-report":
            return MakeReportOperator()
        case "make-data-summary":
            return MakeReportOperator()
        case "apple-make-duration":
            return AppleMakeDurationOperator()
        case "apple-collab-sentence":
            return AppleCollabSentenceOperator()
        case "format-team-researchers":
            return FormatTeamResearchersOperator()
        case "apple-team-researchers":
            return AppleTeamResearchersOperator()
        case "apple-affiliation-demonstration":
            return AppleAffiliationDemonstrationOperator()
        case "apple-publication-answer":
            return ApplePublicationAnswerOperator()
        case "format-funding-summary":
            return FormatFundingSummaryOperator()
        case "format-funding-sources-text":
            return FormatFundingSourcesTextOperator()
        case "commercial-independence-and":
            return CommercialIndependenceAndOperator()
        case "tiktok-affiliation-type":
            return TiktokAffiliationTypeOperator()
        case "format-org-affiliation":
            return FormatOrgAffiliationOperator()
        case "x-commercial-interests":
            return XCommercialInterestsOperator()
        case "apple-funding-disclosure":
            return AppleFundingDisclosureOperator()
        case "apple-funding-breakdown":
            return AppleFundingBreakdownOperator()
        case "google-funding-sponsor-types":
            return GoogleFundingSponsorTypesOperator()
        case "google-funding-org-names":
            return GoogleFundingOrgNamesOperator()
        case "google-funding-disclosure":
            return GoogleFundingDisclosureOperator()
        case "format-tom-summary":
            return FormatTomSummaryOperator()
        case "google-data-protection":
            return GoogleDataProtectionOperator()
        case "apple-rights-protection":
            return AppleRightsProtectionOperator()
        case "apple-purpose-confirmation":
            return ApplePurposeConfirmationOperator()
        case "apple-security-arrangements":
            return AppleSecurityArrangementsOperator()
        case "apple-purpose-limitation":
            return ApplePurposeLimitationOperator()
        case "pinterest-purpose-gate":
            return PinterestPurposeGateOperator()
        case "meta-collab-emails":
            return MetaCollabEmailsOperator()
        case "meta-mcl-research-tools":
            return MetaMclResearchToolsOperator()
        case _:
            raise ValueError(f"Invalid operator description: {operator}")


OPERATOR_REGISTRY: dict[str, OperatorSpec] = {
    "make-iso": OperatorSpec(
        name="make-iso",
        label="Country name → ISO alpha-3",
        input_arity="single",
        description="Converts a country display name to ISO 3166-1 alpha-3 code.",
    ),
    "join-space": OperatorSpec(
        name="join-space",
        label="Join with space",
        input_arity="list",
        description="Joins multiple text values with a single space.",
    ),
    "join-comma": OperatorSpec(
        name="join-comma",
        label="Join with comma",
        input_arity="list",
        description="Joins multiple text values with ', '.",
    ),
    "join-paragraph": OperatorSpec(
        name="join-paragraph",
        label="Join paragraphs",
        input_arity="list",
        description="Joins text sections with blank lines between them.",
    ),
    "join-date-range": OperatorSpec(
        name="join-date-range",
        label="Format date range",
        input_arity="list",
        description="Formats two dates as 'start to end'.",
    ),
    "make-duration": OperatorSpec(
        name="make-duration",
        label="Date range → duration bucket",
        input_arity="list",
        description="Maps a storage/access date range to a duration bucket.",
    ),
    "make-report": OperatorSpec(
        name="make-report",
        label="Combine report sections",
        input_arity="list",
        description="Joins narrative sections (alias for join-paragraph).",
    ),
    "make-data-summary": OperatorSpec(
        name="make-data-summary",
        label="Combine data request summary",
        input_arity="list",
        description="Joins data scope, request, dates, and justification into one narrative.",
    ),
    "apple-make-duration": OperatorSpec(
        name="apple-make-duration",
        label="[Apple] Research duration sentence",
        input_arity="list",
        description=(
            "Formats research-start and research-end as: "
            "'The research project is supposed to run from {start} to {end}.'"
        ),
    ),
    "apple-collab-sentence": OperatorSpec(
        name="apple-collab-sentence",
        label="[Apple] Collaboration confirmation sentence",
        input_arity="single",
        description=(
            "Maps collab-binary Yes/No to Apple's individual vs team confirmation wording."
        ),
    ),
    "format-team-researchers": OperatorSpec(
        name="format-team-researchers",
        label="Format team researchers",
        input_arity="single",
        needs_context=True,
        description=(
            "Formats collab-researchers structured JSON into name, email, and affiliation text."
        ),
    ),
    "apple-team-researchers": OperatorSpec(
        name="apple-team-researchers",
        label="[Apple] Format team researchers",
        input_arity="single",
        needs_context=True,
        description="Formats structured team members for Apple A4.",
    ),
    "apple-affiliation-demonstration": OperatorSpec(
        name="apple-affiliation-demonstration",
        label="[Apple] Affiliation demonstration",
        input_arity="single",
        needs_context=True,
        description=(
            "Formats organisation name, contact details, role, not-for-profit status, "
            "institutional profile, and affiliation evidence for Apple A5."
        ),
    ),
    "apple-publication-answer": OperatorSpec(
        name="apple-publication-answer",
        label="[Apple] Publication answer",
        input_arity="single",
        needs_context=True,
        description=(
            "Maps research-publication-bin Yes/No to Apple's A9 wording; "
            "uses research-publication when Yes."
        ),
    ),
    "format-funding-summary": OperatorSpec(
        name="format-funding-summary",
        label="Format funding summary",
        input_arity="single",
        needs_context=True,
        description=(
            "Maps funding-received Yes/No to a narrative; uses structured "
            "funding-entries when present, otherwise funding-sources text."
        ),
    ),
    "format-funding-sources-text": OperatorSpec(
        name="format-funding-sources-text",
        label="Funding sources free text",
        input_arity="single",
        needs_context=True,
        description=(
            "Returns funding-sources when funded; otherwise 'no sources of funding'."
        ),
    ),
    "commercial-independence-and": OperatorSpec(
        name="commercial-independence-and",
        label="Commercial independence (AND)",
        input_arity="single",
        needs_context=True,
        description=(
            "Yes when person, organisation, and research are all "
            "independent from commercial interests."
        ),
    ),
    "tiktok-affiliation-type": OperatorSpec(
        name="tiktok-affiliation-type",
        label="[TikTok] Affiliation category",
        input_arity="single",
        needs_context=True,
        description="Maps org-type to TikTok T2 affiliation options.",
    ),
    "format-org-affiliation": OperatorSpec(
        name="format-org-affiliation",
        label="Organisation affiliation summary",
        input_arity="single",
        needs_context=True,
        description="Formats organisation name, type, and not-for-profit status.",
    ),
    "x-commercial-interests": OperatorSpec(
        name="x-commercial-interests",
        label="[X] Commercial interests narrative",
        input_arity="single",
        needs_context=True,
        description="Organisational independence from commercial interests plus evidence.",
    ),
    "apple-funding-disclosure": OperatorSpec(
        name="apple-funding-disclosure",
        label="[Apple] Funding disclosure",
        input_arity="single",
        needs_context=True,
        description="Formats funding sources, amounts, and terms for Apple A17.",
    ),
    "apple-funding-breakdown": OperatorSpec(
        name="apple-funding-breakdown",
        label="[Apple] Funding percentage breakdown",
        input_arity="single",
        needs_context=True,
        description="Formats per-source funding percentages for Apple A18.",
    ),
    "google-funding-sponsor-types": OperatorSpec(
        name="google-funding-sponsor-types",
        label="[Google] Funding sponsor types",
        input_arity="single",
        needs_context=True,
        description="Aggregates funding-source-type values for Google G23.",
    ),
    "google-funding-org-names": OperatorSpec(
        name="google-funding-org-names",
        label="[Google] Funding organisation names",
        input_arity="single",
        needs_context=True,
        description="Lists non-self-funded sponsor names for Google G24.",
    ),
    "google-funding-disclosure": OperatorSpec(
        name="google-funding-disclosure",
        label="[Google] Funding disclosure",
        input_arity="single",
        needs_context=True,
        description=(
            "Formats grant year, duration, and amount per source for Google G27."
        ),
    ),
    "format-tom-summary": OperatorSpec(
        name="format-tom-summary",
        label="Format TOM summary",
        input_arity="single",
        needs_context=True,
        description="Joins technical and organisational data protection measures.",
    ),
    "google-data-protection": OperatorSpec(
        name="google-data-protection",
        label="[Google] Data protection narrative",
        input_arity="single",
        needs_context=True,
        description="Formats TOM, GDPR lead, and storage details for Google G32.",
    ),
    "apple-rights-protection": OperatorSpec(
        name="apple-rights-protection",
        label="[Apple] Rights and legitimate interests",
        input_arity="single",
        needs_context=True,
        description="Formats rights-balancing narrative for Apple A13.",
    ),
    "apple-purpose-confirmation": OperatorSpec(
        name="apple-purpose-confirmation",
        label="[Apple] Purpose limitation confirmation",
        input_arity="single",
        needs_context=True,
        description="Confirmation of no other intended data use for Apple A14.",
    ),
    "apple-security-arrangements": OperatorSpec(
        name="apple-security-arrangements",
        label="[Apple] Security arrangements",
        input_arity="single",
        needs_context=True,
        description="TOM, access, storage, and data combination for Apple A19.",
    ),
    "apple-purpose-limitation": OperatorSpec(
        name="apple-purpose-limitation",
        label="[Apple] Purpose limitation controls",
        input_arity="single",
        needs_context=True,
        description="How sole-use for this research is ensured for Apple A22.",
    ),
    "pinterest-purpose-gate": OperatorSpec(
        name="pinterest-purpose-gate",
        label="[Pinterest] Sole research use",
        input_arity="single",
        needs_context=True,
        description="Maps purpose-limitation-binary to Pinterest P18 wording.",
    ),
    "meta-collab-emails": OperatorSpec(
        name="meta-collab-emails",
        label="[Meta] Collaborator emails",
        input_arity="single",
        needs_context=True,
        description="Comma-separated emails from collab-researchers when collaborating.",
    ),
    "meta-mcl-research-tools": OperatorSpec(
        name="meta-mcl-research-tools",
        label="[Meta] MCL research tools",
        input_arity="single",
        needs_context=True,
        description="MCL web tool always; appends API access when selected.",
    ),
    "literal-yes": OperatorSpec(
        name="literal-yes",
        label="Literal Yes",
        input_arity="any",
        constant_output=True,
        description="Always answers Yes without collecting a general question.",
    ),
    "literal-no": OperatorSpec(
        name="literal-no",
        label="Literal No",
        input_arity="any",
        constant_output=True,
        description="Always answers No without collecting a general question.",
    ),
    "literal-value": OperatorSpec(
        name="literal-value",
        label="Literal value",
        input_arity="any",
        constant_output=True,
        description="Always answers a fixed value from mapping.value.",
    ),
}


def operation_constant_output(operation: str) -> bool:
    spec = OPERATOR_REGISTRY.get(operation)
    return bool(spec and spec.constant_output)


def list_operators() -> list[OperatorSpec]:
    return list(OPERATOR_REGISTRY.values())
