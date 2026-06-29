describe('Timeline Filters', () => {
  let createdIds = []
  let token = null

  before(() => {
    cy.request('POST', '/api/admin/login', {
      password: Cypress.env('ADMIN_PASSWORD'),
    }).then(resp => {
      token = resp.body.access_token
    })
  })

  function seedEvents() {
    const events = [
      { title: 'Timeline Test Event 1', date: '2001-12-12T10:00:00' },
      { title: 'Timeline Test Event 2', date: '2004-10-10T12:00:00' },
      { title: 'Timeline Test Event 3', date: '2026-06-16T08:00:00' },
    ]

    const chainable = cy.wrap(null)
    events.forEach(({ title, date }) => {
      chainable.then(() => {
        return cy.request({
          method: 'POST',
          url: '/api/events',
          headers: { Authorization: `Bearer ${token}` },
          body: { title, date, points: null },
        }).then(r => { createdIds.push(r.body.id) })
      })
    })
    return chainable
  }

  function cleanupEvents() {
    createdIds.forEach(id => {
      cy.request({
        method: 'DELETE',
        url: `/api/events/${id}`,
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false,
      })
    })
  }

  beforeEach(() => {
    createdIds = []
    seedEvents().then(() => {
      cy.visit('/')
      cy.get('.timeline', { timeout: 5000 }).should('exist')
    })
  })

  afterEach(() => {
    cleanupEvents()
  })

  it('timeline is always visible even with no matching events', () => {
    cy.get('.filter-left input[type="date"]').type('2099-01-01')
    cy.get('.filter-right input[type="date"]').type('2099-12-31')

    cy.get('.timeline').should('be.visible')
    cy.get('.timeline-empty').should('contain', 'No events in this date range')

    cy.get('.filter-left input[type="date"]').should('be.visible')
    cy.get('.filter-right input[type="date"]').should('be.visible')
    cy.get('.play-btn').should('be.visible')
  })

  it('clearing filters restores events', () => {
    cy.get('.filter-left input[type="date"]').type('2099-01-01')
    cy.get('.filter-right input[type="date"]').type('2099-12-31')

    cy.get('.timeline-empty').should('be.visible')

    cy.get('.filter-left input[type="date"]').clear()

    cy.get('.timeline-item', { timeout: 3000 }).should('have.length.greaterThan', 0)
  })

  it('filtering hides excluded events from sidebar', () => {
    cy.get('.sidebar .event-item').then($items => {
      const initialCount = $items.length
      expect(initialCount).to.be.greaterThan(1)

      cy.get('.filter-left input[type="date"]').type('2099-01-01')

      cy.get('.timeline-empty').should('be.visible')
      cy.get('.sidebar .event-item').should('have.length', 0)
    })
  })
})
