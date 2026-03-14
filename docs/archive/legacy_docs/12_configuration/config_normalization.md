Configuration Normalization

The configuration loader performs normalization to ensure values are safe and consistent.

Normalization occurs inside:

load_config()
URL Normalization

The vast_api_url field is normalized to prevent malformed requests.

Example problematic inputs:

"https://console.vast.ai/api/v0"
'https://console.vast.ai/api/v0/'

Normalized result:

https://console.vast.ai/api/v0

Steps applied:

Trim whitespace

Remove surrounding quotes

Remove trailing slash

Quote Removal

Some YAML parsing scenarios leave surrounding quotes.

Example input:

vast_api_url: '"https://console.vast.ai/api/v0"'

Normalization removes outer quotes.

Trailing Slash Removal

Trailing slashes cause double-slash URLs.

Example bad endpoint:

https://console.vast.ai/api/v0//bundles

Normalization ensures final URL is:

https://console.vast.ai/api/v0/bundles
Scalar Normalization

Fallback config parser normalizes scalars.

Supported types:

string
integer
float
boolean

Example conversions:

"true" -> True
"100" -> 100
"0.6" -> 0.6
Determinism Guarantee

Normalization ensures configuration values are identical regardless of:

YAML quoting

trailing slashes

whitespace

This ensures deterministic behavior across environments.