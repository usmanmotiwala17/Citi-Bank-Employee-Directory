import { Box, Typography } from '@mui/material'
import { CITI_BLUE, CITI_RED } from '../theme'

export default function CitiLogo({ fontSize = '1.5rem' }) {
  return (
    <Box sx={{ position: 'relative', display: 'inline-block', pt: 1 }}>
      <svg
        width="38" height="16" viewBox="0 0 38 16"
        style={{ position: 'absolute', top: -2, left: 4 }}
      >
        <path d="M2 14 C 2 3, 36 3, 36 14" fill="none" stroke={CITI_RED} strokeWidth="3" strokeLinecap="round" />
      </svg>
      <Typography sx={{ fontWeight: 800, fontSize, color: CITI_BLUE, letterSpacing: '-0.5px', lineHeight: 1 }}>
        citi
      </Typography>
    </Box>
  )
}
