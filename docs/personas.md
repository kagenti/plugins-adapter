# Personas

Here are some personas that would leverage the plugins adapter at runtime (runtime personas), configure and deploy it (deployment personas), and develop for it (developer personas).

## Runtime personas
- Agent user: "I want to run my agent with tools"
- Plugin utilizer: "I've tried out plugins from Context Forge or guardrails from Nemo. I want to use those same capabilities through the gateway"

## Deployment personas
- Platform ops/administrator: "I need to configure guardrail plugins for Customer W's agent application"

## Developer personas
- Plugin writer: "I have a shiny new prompt injection detection algorithm, and I want people to try it out in their agent applications"
- Plugin adapter writer: "I'm making and maintaining a component that will 1. let plugin writers bring their plugins and 2. help the gateway organize the priority, order, and way to call different plugins"

Illustrated persona stories are included [in this diagram](./plugin_user_stories.png). Note that configurations and APIs are not finalized.
