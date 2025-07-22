import "vuetify/styles";
import { createVuetify } from "vuetify";
import {
  VApp,
  VForm,
  VTextField,
  VBtn,
  VAlert,
  VContainer,
  VCard,
  VRow,
  VCol,
  VCardTitle,
  VCardText,
  VCardActions,
  VImg,
  VChip,
  VCardSubtitle,
  VIcon,
  VBtnToggle,
  VTable,
  VList,
  VListItem,
  VListItemTitle,
  VListItemSubtitle,
  VFileInput,
  VAppBar,
  VNavigationDrawer,
  VDivider,
  VLayout,
} from "vuetify/components";
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components: {
    VApp,
    VForm,
    VTextField,
    VBtn,
    VAlert,
    VContainer,
    VCard,
    VRow,
    VCol,
    VCardTitle,
    VCardText,
    VImg,
    VChip,
    VCardSubtitle,
    VIcon,
    VBtnToggle,
    VTable,
    VList,
    VListItem,
    VListItemTitle,
    VListItemSubtitle,
    VFileInput,
    VAppBar,
    VNavigationDrawer,
    VDivider,
    VLayout
  },
  defaults: {
    VTextField: {
      variant: "outlined",
      density: "compact", // You can change this to 'filled', 'solo', etc.
    },
    // Add more component defaults here if needed
  },
  theme: {
    defaultTheme: "light",
    themes: {
      light: {
        colors: {
          primary:   "#1976D2", // Blue (main actions)
          secondary: "#424242", // Dark Grey (secondary actions)
          accent:    "#FFB300", // Amber (highlights)
          success:   "#2E7D32", // Green (success)
          info:      "#0288D1", // Cyan (info)
          warning:   "#F9A825", // Amber dark (warning)
          error:     "#D32F2F", // Red (error)
          background: "#F5F7FA", // Light background
          surface:   "#FFFFFF", // Cards, surfaces
        },
      },
    },
  },
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
});
