import { Avatar } from '@mui/material'
import { CITI_BLUE } from '../theme'

export default function EmployeeAvatar({ employee, size = 56 }) {
  const initials = `${employee?.first_name?.[0] || ''}${employee?.last_name?.[0] || ''}`.toUpperCase()

  return (
    <Avatar
      sx={{
        width: size,
        height: size,
        bgcolor: CITI_BLUE,
        color: '#ffffff',
        fontWeight: 700,
        fontSize: size * 0.36,
      }}
    >
      {initials || '?'}
    </Avatar>
  )
}
