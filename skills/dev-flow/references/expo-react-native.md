# Expo and React Native

Use this reference for the affected package that declares `expo` or `react-native`. In a mixed monorepo, route a Next.js or other web package by its own manifest and runtime.

## Discover the target

- Read the package scripts, Expo SDK or React Native version, app configuration, and the nearest related screen. Inspect native projects and config plugins when the change crosses the native boundary.
- Identify the active navigation, theme and state patterns. Check whether the project runs in Expo Go, a development build, or a bare native app before choosing how to launch it.
- Use the repository's installed package manager and scripts. For version-specific APIs, check the documentation for its Expo SDK or React Native version.

## Build native UI

- Use the existing native primitives, theme, and navigation conventions. Apply safe-area insets and keyboard avoidance using the approach already established in the app.
- Check platform text scaling, accessibility labels and roles, touch targets, and Android back behavior or iOS gestures where they affect the flow. Preserve reduced-motion preferences for animated interactions.
- For Expo projects, use `expo-native-ui` for native screen patterns or `expo-design-system` for theming and tokens when the relevant skill is available. Follow [Web and Mobile UI](ui-ux.md) when implementing a new screen or a material UI change.

## Verify on the affected platform

Run the project's configured checks, then launch the affected route in the project's simulator, emulator, or local test device. Exercise navigation and the relevant loading, error, or recovery states. If iOS and Android are both affected, verify each available platform and list any missing coverage. Use the project's authorized local workflow for development builds and native dependencies.
