Security Boundaries
Hard Rules

no shell=True

no uncontrolled background daemons by default

no unrestricted filesystem writes

no path traversal outside allowed workspace

no implicit environment inheritance of secrets

no silent network actions unless explicitly allowed

Future Expansion

Higher-trust local modes may widen some capabilities, but all changes must remain explicit and policy-controlled.