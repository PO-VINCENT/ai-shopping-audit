# CatalogReady Browser Extension Privacy Policy

**Effective date:** July 13, 2026

This policy describes how the CatalogReady browser extension handles data. It
applies to the extension distributed through the Chrome Web Store and used with
the user-operated CatalogReady local service.

## What the extension handles

CatalogReady handles the following data only when a user opens the extension
and explicitly starts an audit:

- **Web history:** the URL of the active product page selected by the user.
- **Website content:** the rendered HTML of that active page, including its
  visible text, links, images, and structured product data.

The extension also stores these preferences locally in the browser:

- the CatalogReady local server URL;
- the selected model-provider name and model identifier; and
- the selected interface language.

The extension does not ask for or store passwords, authentication tokens,
payment information, or model-provider API keys. Provider keys remain in the
user-operated local service environment.

## How data is used

The active page URL and rendered HTML are sent to the CatalogReady service URL
configured by the user. By default, this is a loopback address on the user's
own computer (`http://127.0.0.1:8080`). The local service uses the data only to:

- calculate comprehensive and platform-specific AI-shopping readiness scores;
- identify evidence-based findings and deductions;
- generate merchant questions and recommended fixes;
- compare the rendered page with public static HTML when requested; and
- generate reports requested by the user.

CatalogReady does not monitor browsing in the background. It does not access a
page until the user invokes the extension, and it does not modify the page or
write to a storefront.

## Optional model providers

The default deterministic audit does not require a model provider and sends no
page data to one. If the user deliberately selects and configures an external
model provider in the local CatalogReady service, the service may send the
minimum relevant product evidence, findings, or audit context needed for the
requested model-assisted feature to that provider. Supported providers include
OpenAI, Google Gemini, Anthropic, and DeepSeek. That processing is governed by
the terms and privacy policy of the provider selected by the user.

CatalogReady does not send page data to a developer-controlled analytics,
advertising, or profiling service.

## Storage and retention

The extension does not persist page HTML, page URLs, or audit results in Chrome
storage. Audit results exist in the popup while it is open and are discarded
when that popup is closed. The local CatalogReady service does not persist audit
requests or results by default.

Locally stored preferences remain until the user changes them, clears the
extension's storage, or removes the extension.

If a user enables an external model provider, that provider's retention and
deletion practices apply to data processed by it.

## Sharing, selling, and advertising

CatalogReady does not sell user data. It does not use or transfer user data for
advertising, creditworthiness, lending, profiling, or unrelated purposes. Data
is handled only to provide the user-requested product-page audit and related
output described above.

CatalogReady's use and transfer of information received from Chrome APIs
adheres to the Chrome Web Store User Data Policy, including the Limited Use
requirements.

## Security

The extension limits page access to the active tab selected by the user and
limits host access to loopback addresses (`localhost` and `127.0.0.1`). It does
not request persistent access to all websites. Connections from the local
service to an optional external model provider use that provider's HTTPS API.

## User choices and deletion

Users can avoid all page access by not starting an audit. They can use the
deterministic provider option to avoid model-provider processing. Users can
delete locally stored extension preferences by clearing the extension's data or
uninstalling CatalogReady.

## Changes to this policy

This policy may be updated when CatalogReady's data practices change. The
effective date above will be revised, and material changes will be disclosed in
the extension listing or interface as required.

## Contact

Questions or requests about this policy can be sent to:

**Vincent Po Li**  
[vincentli802@hotmail.com](mailto:vincentli802@hotmail.com)  
[CatalogReady GitHub repository](https://github.com/PO-VINCENT/ai-shopping-audit)
