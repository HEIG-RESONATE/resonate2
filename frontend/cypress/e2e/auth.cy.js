describe('Admin Auth', () => {
  it('logs in with correct password', () => {
    cy.visit('/admin')
    cy.get('input[type="password"]').type(Cypress.env('ADMIN_PASSWORD'))
    cy.get('button[type="submit"]').click()
    // Should see the event form after login
    cy.get('input[placeholder="Event title"]', { timeout: 5000 }).should('exist')
    cy.contains('nav', 'Admin').should('exist')
  })

  it('shows error on wrong password', () => {
    cy.visit('/admin')
    cy.get('input[type="password"]').type('wrongpassword')
    cy.get('button[type="submit"]').click()
    cy.get('.error', { timeout: 5000 }).should('contain', 'Wrong password')
    // Should stay on login page
    cy.get('input[type="password"]').should('exist')
  })

  it('can create and delete an event', () => {
    // Login
    cy.login()

    // Fill in event form
    cy.get('input[placeholder="Event title"]').type('Cypress Test Event')
    cy.get('input[type="datetime-local"]').type('2026-07-20T14:00')

    // Submit
    cy.get('.event-form button[type="submit"]').click()

    // Should appear in the table
    cy.contains('.events-table td', 'Cypress Test Event').should('exist')

    // Delete it
    cy.contains('tr', 'Cypress Test Event').within(() => {
      cy.get('.btn-danger').click()
    })

    // Confirm deletion if dialog appears
    cy.on('window:confirm', () => true)

    // Should be gone
    cy.contains('.events-table td', 'Cypress Test Event').should('not.exist')
  })

  it('can navigate to map and back', () => {
    cy.login()

    // Click Map link
    cy.contains('a', 'Map').click()
    cy.url().should('include', '/')

    // Go back to admin via URL
    cy.visit('/admin')
    cy.get('input[placeholder="Event title"]', { timeout: 5000 }).should('exist')
  })

  it('persists auth across page reload', () => {
    cy.login()

    // Reload
    cy.reload()

    // Should still be authenticated
    cy.get('input[placeholder="Event title"]', { timeout: 5000 }).should('exist')
  })
})
