import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import { VForm, VTextField, VBtn, VAlert, VContainer, VCard, VRow, VCol, VCardTitle, VCardText, VCardActions, VImg, VChip, VCardSubtitle, VIcon, VBtnToggle, VTable } from 'vuetify/components'

export default createVuetify({
  components: {
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
  },
  defaults: {
    VTextField: {
      variant: 'outlined',
      density: 'compact', // You can change this to 'filled', 'solo', etc.
    },
    // Add more component defaults here if needed
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#2c3e50',
          secondary: '#424242',
          // ...add more colors as needed
        },
      },
    },
  },
})