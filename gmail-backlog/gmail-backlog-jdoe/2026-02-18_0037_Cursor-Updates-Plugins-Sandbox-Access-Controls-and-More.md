# Cursor Updates: Plugins, Sandbox Access Controls, and More

- **Date:** Wed, 18 Feb 2026 00:37:26 +0000
- **From:** Cursor Team <team@mail.cursor.com>
- **To:** f.zakirkhojaeva@rantsports.com

---

Hi Feruza,

In Cursor 2.5, we introduced plugins for extending Cursor, improvements to core agent capabilities like subagents, and fine-grained network controls for sandboxed commands.

Plugins on the Cursor Marketplace

Cursor now supports plugins ( https://cursor.com/docs/plugins ), allowing agents to connect to external tools and learn new knowledge. Plugins bundle capabilities like MCP servers, skills, subagents, rules, and hooks that extend agents with custom functionality.

We’re starting with a highly curated set from partners such as Amplitude, AWS, Figma, Linear, and Stripe. These plugins span the product development lifecycle, allowing Cursor to deploy services, implement payments, run advanced testing, and more.

Explore Cursor Marketplace ( https://cursor.com/marketplace )
You can discover and install prebuilt plugins on the Cursor Marketplace ( https://cursor.com/marketplace ) or create your own and share them with the community.

Read more in our announcement ( https://cursor.com/blog/marketplace ).

Sandbox network access controls

The sandbox ( https://cursor.com/docs/agent/terminal#sandbox-configuration ) now supports granular network access controls, as well as controls for access to directories and files on your local filesystem. Define exactly which domains the agent is allowed to reach while running sandboxed commands.

Admins on the Enterprise plan can enforce network allowlists and denylists from the admin dashboard ( https://cursor.com/dashboard ), ensuring organization-wide egress policies apply to all agent sandbox sessions.

Async subagents

Previously, all subagents ( https://cursor.com/docs/context/subagents ) ran synchronously, blocking the parent agent until they complete. Subagents can now run asynchronously, allowing the parent to continue working while subagents run in the background.

Subagents can also spawn their own subagents, creating a tree of coordinated work. This allows Cursor to take on bigger tasks like multi-file features, large refactors, and challenging bugs.

Learn about everything new in Cursor 2.5 ( https://cursor.com/changelog/2-5 ), including performance improvements to subagents, chat history as context, and more.

Best,
Cursor Team

Unsubscribe ( https://track.customer.io/unsubscribe/dgT_pwsDAO6NyB7tjcgeAZxt2N7fqIlIUq6_Rt9juA== )

