# UI KNOWLEDGE BASE

## OVERVIEW
Frontend for the Semantic File System. Built with Vanilla JS, custom state management, and Vite.

## STRUCTURE
```
ui/
├── js/
│   ├── components/    # Reusable UI components (Sidebar, Explorer, Auth)
│   ├── app.js         # Main application entry and routing
│   ├── api.js         # Backend API integration layer
│   └── state.js       # Global state management
└── css/               # Modular CSS (main, components, transitions)
```

## WHERE TO LOOK
| Component | File | Description |
|-----------|------|-------------|
| Navigation | `js/components/sidebar.js` | Sidebar and storage source selection |
| Auth Flow | `js/components/auth.js` | Login, Register, and Guest access |
| File Browser| `js/components/explorer.js`| File grid/list view and navigation |
| State | `js/state.js` | Global application state |

## CONVENTIONS
- **State Management**: Use `state.subscribe()` for reactive renders in components.
- **Rendering**: Components use template literals for HTML generation.
- **Icons**: Always call `lucide.createIcons()` after DOM updates.

## ANTI-PATTERNS
- Do not hardcode API URLs; use constants in `api.js`.
- Never manipulate the DOM directly from `state.js`.

## RECENT CHANGES / TODOs
- Remove "Local Files" from storage options.
- Remove "Favourites" and "Recent" views.
- Update Guest login to show "Sign in with Google" and warnings.
- Remove Email/Password authentication.
