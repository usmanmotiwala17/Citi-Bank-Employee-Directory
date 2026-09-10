import { createTheme } from '@mui/material/styles'

// Citi-style palette - Citi blue, a small red accent, white, and black only.
export const CITI_BLUE = '#056DAE'
export const CITI_BLUE_DARK = '#045688'
export const CITI_RED = '#EE3831'

export const theme = createTheme({
  palette: {
    primary: { main: CITI_BLUE, contrastText: '#ffffff' },
    secondary: { main: CITI_RED, contrastText: '#ffffff' },
    background: { default: '#f4f6f8', paper: '#ffffff' },
    text: { primary: '#111111', secondary: '#4a4a4a' },
    divider: '#e2e5e9',
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600 },
      },
    },
  },
})
