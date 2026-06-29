// ***********************************************
// Custom commands for auth tests
// ***********************************************

Cypress.Commands.add('login', (password) => {
  cy.visit('/admin')
  cy.get('input[type="password"]').type(password || Cypress.env('ADMIN_PASSWORD'))
  cy.get('button[type="submit"]').click()
  // Wait for navigation to event form
  cy.get('input[placeholder*="Event title"]', { timeout: 5000 }).should('exist')
})
