import { NavLink } from 'react-router-dom'
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Badge, Typography, Divider, Button,
} from '@mui/material'
import PeopleAltIcon from '@mui/icons-material/PeopleAlt'
import AssignmentIcon from '@mui/icons-material/Assignment'
import PersonIcon from '@mui/icons-material/Person'
import LogoutIcon from '@mui/icons-material/Logout'
import { useAuth } from '../context/AuthContext'
import { CITI_BLUE, CITI_RED } from '../theme'
import CitiLogo from './CitiLogo'

export const SIDEBAR_WIDTH = 250

export default function Sidebar() {
  const { employee, logout, pendingCount } = useAuth()
  const canSeeRequests = employee.role === 'CEO' || employee.role === 'MANAGER'

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          bgcolor: '#ffffff',
          borderRight: '1px solid #e2e5e9',
          display: 'flex',
        },
      }}
    >
      <Box sx={{ px: 2.5, py: 3 }}>
        <CitiLogo />
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
          Employee Directory
        </Typography>
      </Box>
      <Divider />
      <List sx={{ flexGrow: 1, py: 1 }}>
        <NavItem to="/" end icon={<PeopleAltIcon />} label="Employee Directory" />
        {canSeeRequests && (
          <NavItem to="/requests" icon={<AssignmentIcon />} label="Requests" badge={pendingCount} />
        )}
        <NavItem to="/profile" icon={<PersonIcon />} label="My Profile" />
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" sx={{ mb: 1.5, color: 'text.secondary' }}>
          {employee.first_name} {employee.last_name}
          <br />
          <strong>{employee.role}</strong>
        </Typography>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<LogoutIcon />}
          onClick={logout}
          sx={{ borderColor: CITI_BLUE, color: CITI_BLUE }}
        >
          Log Out
        </Button>
      </Box>
    </Drawer>
  )
}

function NavItem({ to, end, icon, label, badge }) {
  return (
    <ListItemButton
      component={NavLink}
      to={to}
      end={end}
      sx={{
        mx: 1,
        borderRadius: 1.5,
        '&.active': {
          bgcolor: '#e6f2fb',
          color: CITI_BLUE,
          '& .MuiListItemIcon-root': { color: CITI_BLUE },
        },
      }}
    >
      <ListItemIcon sx={{ minWidth: 40, color: '#000000' }}>{icon}</ListItemIcon>
      <ListItemText primary={label} />
      {!!badge && (
        <Badge
          badgeContent={badge}
          sx={{ '& .MuiBadge-badge': { bgcolor: CITI_RED, color: '#ffffff', fontWeight: 700 } }}
        />
      )}
    </ListItemButton>
  )
}
