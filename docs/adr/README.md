# Socorro Architecture Decision Records

## Development

If not already done, install Log4brains:

```bash
npm install -g log4brains
```

To preview the knowledge base locally, run:

```bash
log4brains preview
```

In preview mode, the Hot Reload feature is enabled: any change you make to a
markdown file is applied live in the UI.

To create a new ADR interactively, run from the repository root:

```bash
log4brains adr new
```

## ADR flow over time

### Create ADRs for critical decisions

We create ADRs to discuss and document critical architecture decisions. Create
the ADR, create a pull request on GitHub for it, then discuss the details with
stakeholders and peers.

In general, if a decision doesn't seem critical, then it probably isn't. We
want to minimize the number of ADRs we have to reduce the amount of time it
takes for a new person to come up to speed and also to reduce ongoing
maintenance.

If we find multiple people asking about a specific architecture decision that
doesn't have a corresponding ADR, we can backfill the ADR.

### Update stale ADRs

When an ADR is stale, it should be updated. Historical changes to ADRs can be
found by looking at the git commits.

### Delete obsolete ADRs

When ADRs are no longer relevant, they should be deleted. Make sure to go
through ADRs that reference the deleted ADR and update them.

## More information

- [Log4brains documentation](https://github.com/thomvaill/log4brains/tree/master#readme)
- [What is an ADR and why should you use them](https://github.com/thomvaill/log4brains/tree/master#-what-is-an-adr-and-why-should-you-use-them)
- [ADR GitHub organization](https://adr.github.io/)
