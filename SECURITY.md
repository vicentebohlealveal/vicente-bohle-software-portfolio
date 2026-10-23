# Security notes

- Never commit `.env`, API keys, passwords, private certificates, or Supabase service-role/secret keys.
- The Kong.3d portfolio source uses placeholder values for Supabase. Configure your own project and validate Row Level Security policies before enabling cloud sync.
- Do not publish private inventory exports, user data, or unredacted logs.
- Treat generated scientific claims and outputs from AI tools as drafts that require human verification.
