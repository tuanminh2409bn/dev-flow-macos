# Web and Mobile UI

Identify the screen, the primary user action, and the target platform. Read the nearest comparable screen and its components, theme tokens, assets, and interaction patterns. Follow any design guidance maintained in the repo, such as `DESIGN.md`. For an implementation request, treat the approved reference as authoritative for visible design decisions. Raise conflicts that materially affect usability, accessibility, or fidelity.

## Work from the available design

- **Figma frame.** When Figma MCP is available and authorized, inspect the linked frame and relevant variants. Use the screenshot as a visual baseline and the design context to identify layout, variables, and assets. Use Code Connect mappings when present. Map these to the project's existing components and target framework. If the frame is inaccessible, use available exports and record which decisions could not be verified. Request an export if the missing design blocks implementation.
- **Mockup or screenshot.** Record the visible hierarchy, type scale, spacing, color, and assets. Infer flexible layout and interaction using the project's patterns. State material assumptions about fonts, dimensions, undisplayed breakpoints, or states. Use authorized source assets when available and flag meaningful substitutions.
- **Design direction is open.** Establish a direction that fits the product and existing visual language. Choose one available design skill for this step when it adds value.
  - **Anthropic `frontend-design`** is the default for original web screens that need visual direction, hierarchy, typography, and layout.
  - **UI UX Pro Max** fits work that needs a new palette, type scale, design tokens, or UX patterns for a web or mobile product. Keep established project tokens unless a redesign calls for changing them.
  - **Taste Skill** fits brand-led landing pages and marketing websites where art direction, imagery, and page rhythm are central.

## Implement the interaction

Use `frontend-ui-engineering` for complex web component or state work where available, or a specialist for the relevant native platform when it adds stack-specific guidance.

- Reuse the existing component library, tokens, fonts, and icons. Build the screen with the framework's layout primitives so it can reflow as content or the viewport changes.
- For web projects that use shadcn/ui or a compatible registry, use **shadcn/ui MCP** when available to look up needed components or blocks after checking the codebase for an existing implementation. Follow the project's rules for adding components and dependencies.
- Make hierarchy and the primary action clear. Preserve recognizable controls and readable text. Cover the states that affect the user journey, such as loading, empty results, errors and recovery, or disabled actions. Use the project's navigation and data contracts.
- Check contrast and meaningful labels. For web, use semantic controls and verify keyboard navigation and visible focus. For mobile, use platform accessibility labels, respect safe areas and text scaling, and account for touch targets and the on-screen keyboard where relevant. Respect reduced-motion settings for meaningful animation.

## Verify the rendered result

Run the project's available checks. Render the affected screen with tools already available and compare it to the source design. Compare at the reference size with comparable content where possible. Check hierarchy, type, spacing, alignment, assets, and unexpected clipping. Correct significant differences and recheck the changed screen.

- **Web.** Use the available browser or Chrome DevTools. Check the reference viewport plus representative narrow and wide sizes where supported. Exercise the primary action and affected states, including keyboard and focus for changed controls.
- **Mobile.** Use the project's simulator, emulator, or test device. Exercise the primary flow and the affected navigation and input states. Check layout on a representative small screen and at larger text sizes where relevant. For a cross-platform change, test each affected platform that is available and name the ones still pending.
- For a web redesign or a requested polish pass, use **Impeccable** when available to critique or refine a specific rendered screen or component. Recheck applicable design references and project tokens after changes.

Report the screens, viewport or device, and states actually checked. Include screenshot paths when captured and call out material deviations, assumptions, or checks still pending.
