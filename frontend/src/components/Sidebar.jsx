import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Badge, Typography, Divider, Button, AppBar, Toolbar, IconButton,
  useMediaQuery, useTheme,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import PeopleAltIcon from '@mui/icons-material/PeopleAlt'
import AssignmentIcon from '@mui/icons-material/Assignment'
import PersonIcon from '@mui/icons-material/Person'
import LogoutIcon from '@mui/icons-material/Logout'
import { useAuth } from '../context/AuthContext'
import { CITI_BLUE, CITI_RED } from '../theme'
import { roleLabel } from '../utils/roleLabel'
import CitiLogo from './CitiLogo'

export const SIDEBAR_WIDTH = 250

export default function Sidebar() {
  const { employee, logout, pendingCount } = useAuth()
  const canSeeRequests = employee.role === 'ADMIN' || employee.role === 'MANAGER'
  const theme = useTheme()
  // Below `md`, a fixed sidebar would eat too much of the screen - swap it
  // for a hamburger-triggered temporary (overlay) drawer instead.
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [mobileOpen, setMobileOpen] = useState(false)

  const navContent = (
    <>
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
          <strong>{roleLabel(employee.role)}</strong>
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
    </>
  )

  if (isMobile) {
    return (
      <>
        <AppBar
          position="fixed"
          elevation={0}
          sx={{ bgcolor: '#ffffff', color: '#000000', borderBottom: '1px solid #e2e5e9' }}
        >
          <Toolbar>
            <IconButton
              edge="start"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
              sx={{ mr: 1.5 }}
            >
              <MenuIcon />
            </IconButton>
            <CitiLogo />
          </Toolbar>
        </AppBar>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: SIDEBAR_WIDTH,
              boxSizing: 'border-box',
              bgcolor: '#ffffff',
            },
          }}
        >
          {/* Close the drawer on any click inside it (a nav item or Log Out),
              not just on the backdrop. */}
          <Box onClick={() => setMobileOpen(false)} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {navContent}
          </Box>
        </Drawer>
      </>
    )
  }

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
      {navContent}
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
