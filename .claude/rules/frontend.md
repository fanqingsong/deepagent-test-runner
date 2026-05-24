# Frontend Development

## ⚠️ Design System Requirement

**ALWAYS consult DESIGN.md before writing UI code.**

This project uses an IBM Carbon-inspired design system. Before creating or modifying any UI components:

1. Read DESIGN.md for complete design system specifications
2. Follow the design tokens - Use `--cds-*` naming convention for CSS variables
3. Apply Carbon principles - 0px border-radius, flat design, IBM Plex Sans typography
4. Use the color palette - IBM Blue 60 (#0f62fe) as the sole accent color

### Design System Highlights

- **Border-radius**: 0px on buttons, inputs, cards (24px only for tags/labels)
- **Colors**: Monochromatic grays + IBM Blue 60 (#0f62fe)
- **Typography**: IBM Plex Sans (weight 300/400/600 - NO weight 700)
- **Spacing**: 8px base unit, 16px component padding, 48px button height
- **Depth**: Background-color layering, not shadows (flat design)
- **Inputs**: Bottom-border only, #f4f4f4 background

## Routing

Hash-based routing: `#dashboard`, `#studio`, `#schedules`

## API Calls

- **Via Nginx**: `http://localhost:8080/api/v1/`
- **Direct to backend**: `http://localhost:8011/api/v1/`
- **Analytics**: `http://localhost:8080/api/v1/analytics/`
- **Vite dev**: Use same-origin `/api/v1`

## Frontend Structure

```
frontend/src/
├── pages/          # Page-level components (DashboardPage, StudioPage, SchedulesPage)
├── components/     # Reusable UI components
├── services/       # API service layer
├── hooks/          # Custom React hooks
├── contexts/       # React context providers
└── App.jsx         # Main routing and layout component
```

## State Management

- Direct state updates for simple cases
- `refreshKey` pattern to trigger list refreshes after CRUD operations
- Context providers for shared state (auth, notifications)

## UI Modification Guidelines

- Always check DESIGN.md first for the correct patterns
- Prefer creating new components following the design system over patching old ones
- Test responsive behavior at 320px, 672px, 1056px, and 1312px breakpoints
- All save/submit/delete operations must show visible success or failure messages
