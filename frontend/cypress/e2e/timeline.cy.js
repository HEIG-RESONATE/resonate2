describe('Timeline Filters', () => {
  beforeEach(() => {
    cy.visit('/')
    cy.get('.timeline', { timeout: 5000 }).should('exist')
  })

  it('timeline is always visible even with no matching events', () => {
    // Set dates that exclude all events
    cy.get('.filter-left input[type="date"]').type('2099-01-01')
    cy.get('.filter-right input[type="date"]').type('2099-12-31')

    // Timeline should still be visible
    cy.get('.timeline').should('be.visible')
    cy.get('.timeline-empty').should('contain', 'No events in this date range')

    // Filters should still be accessible
    cy.get('.filter-left input[type="date"]').should('be.visible')
    cy.get('.filter-right input[type="date"]').should('be.visible')
    cy.get('.play-btn').should('be.visible')
  })

  it('clearing filters restores events', () => {
    // Set dates that exclude all events
    cy.get('.filter-left input[type="date"]').type('2099-01-01')
    cy.get('.filter-right input[type="date"]').type('2099-12-31')

    // Verify no events shown
    cy.get('.timeline-empty').should('be.visible')

    // Clear the from date
    cy.get('.filter-left input[type="date"]').clear()

    // Events should reappear
    cy.get('.timeline-item', { timeout: 3000 }).should('have.length.greaterThan', 0)
  })

  it('filtering hides excluded events from sidebar', () => {
    // Record initial sidebar count
    cy.get('.sidebar .event-item').then($items => {
      const initialCount = $items.length
      expect(initialCount).to.be.greaterThan(1)

      // Set "from" far in the future so nothing matches
      cy.get('.filter-left input[type="date"]').type('2099-01-01')

      // Timeline should show empty message
      cy.get('.timeline-empty').should('be.visible')

      // Sidebar should also be empty
      cy.get('.sidebar .event-item').should('have.length', 0)
    })
  })
})
