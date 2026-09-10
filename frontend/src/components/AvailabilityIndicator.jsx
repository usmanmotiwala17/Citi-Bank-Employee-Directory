import { Box, Typography } from '@mui/material'
import { AVAILABLE_GREEN, CITI_RED } from '../theme'

export default function AvailabilityIndicator({ status, sx }) {
  const isAvailable = status !== 'unavailable'

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, ...sx }}>
      <Box
        sx={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          bgcolor: isAvailable ? AVAILABLE_GREEN : CITI_RED,
          flexShrink: 0,
        }}
      />
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
        {isAvailable ? 'Available' : 'Unavailable'}
      </Typography>
    </Box>
  )
}
