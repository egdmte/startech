# CAM Schema Registry and Variable-Reconciliation Design

> Status: design proposal for the standalone CAM prototypes.
> This file does not change the current vehicle configuration contract, validate
> real hardware, or authorize a calibration for use on the physical car.

## Why these screens should be designed now

CAM's fixed controls can remain ordinary hand-designed pages. Module variables that
may change over time need a separate reconciliation flow. Designing that flow before
connecting CAM to YAREN makes the required states visible and prevents the web UI from
silently inventing fields when a profile, server, and car understand different schema
versions.

The reconciliation pages should be designed before production integration. They are
mostly list, form, warning, and review screens, so they are less dependent on the final
car illustration than the interactive component editors.

## Responsibility boundary

```text
CAM fixed pages + generated variable controls
                    |
                    v
             CAM draft profile
                    |
                    v
        Persistent schema registry
                    |
                    v
 YAREN version check, validation, revision and signing
                    |
                    v
        Immutable active configuration
                    |
                    v
 ARDA -> KASIM / KEREM / KADER / OSMAN / 3awnt
```

- **CAM** renders known controls, builds a draft, and explains mismatches.
- **The schema registry** stores immutable, versioned module definitions. It must be
  persisted in version-controlled files or a database; server uptime or process memory
  is not authoritative storage.
- **YAREN** verifies versions, validates structure and relationships, creates revisions,
  and refuses unsupported configurations.
- **Each owning module** implements the meaning of its variables. A JSON definition can
  validate data, but it cannot create new driving behavior by itself.
- **3awnt** may validate declarations and relationships. It does not prove that a value
  was physically measured or that the car is safe.

## Stable profile shape

The outer document should change rarely. Each module section can evolve independently.

```json
{
  "profile_version": 2,
  "profile_id": "example-profile-id",
  "revision": 4,
  "modules": {
    "OSMAN": {
      "schema_version": 2,
      "values": {}
    },
    "KASIM": {
      "schema_version": 1,
      "values": {}
    }
  }
}
```

This is a proposed future shape, not a replacement for the existing v1 files.

## Variable definition shape

```json
{
  "module": "OSMAN",
  "schema_version": 2,
  "variables": {
    "loss_of_command_action": {
      "type": "enum",
      "allowed": [
        "invalidate_request",
        "disarm_wait",
        "refer_validated_commands"
      ],
      "default": "disarm_wait",
      "required": true,
      "safety_class": "critical",
      "consumer": "OSMAN"
    }
  }
}
```

Adding or changing a variable creates a new schema version. An old schema version is
never edited in place.

## Version decisions

Not every mismatch means “add a variable.” CAM and YAREN must classify it first.

| Situation | Required response |
| --- | --- |
| Profile and supported schema match | Open the ordinary editor. |
| Profile is older than the supported schema | Offer an explicit migration and create a new revision. |
| Profile is newer than the server understands | Block editing and require a server/registry update. |
| Server schema is newer than the car supports | Block activation and require a compatible car update or older schema. |
| A new optional value is absent | Show the declared default, then write it only into a new revision. |
| An authorized variable definition is missing | Open the add-variable flow. |
| A variable is unknown, malformed, or has no owner | Fail closed and show a diagnostic; do not guess. |

## Proposed screen sequence

### 1. Schema check

Use the same simple, staged presentation as the existing integrity/preflight screen.
List each module and progressively show:

- profile schema version;
- registry schema version;
- car-supported version, if a car is connected;
- `MATCHED`, `MIGRATION AVAILABLE`, `SERVER UPDATE REQUIRED`,
  `CAR UPDATE REQUIRED`, or `UNKNOWN VARIABLE`.

The primary action remains disabled until all checks finish. A mismatch automatically
routes to the appropriate explanation instead of opening an editable form.

### 2. Reconciliation overview

Show one row per difference with three visually distinct groups:

- **Can migrate automatically** — defaults or compatible renames with declared rules.
- **Needs a definition** — an authorized new variable with missing metadata.
- **Cannot continue** — newer/unknown schema, missing module owner, or incompatible car.

Selecting a row opens its details. The screen must not present “Add variable” for an
incompatible runtime or unsupported behavior.

### 3. Add variable

This can follow the layout of the existing centred “hand” pages: one focused form,
strong status heading, Back/Abort at the top, and session progress at the bottom.

Required fields:

- owning module;
- stable machine key;
- user-facing label and explanation;
- value type;
- allowed values or numeric boundaries;
- default value;
- required/optional state;
- safety classification;
- consuming module or adapter;
- schema version in which it is introduced;
- migration behavior for older profiles;
- whether the runtime already implements the behavior;
- evidence/test reference for that implementation.

For critical values, CAM should also display provenance requirements and mark the
definition as incomplete until an owner and runtime consumer are declared.

### 4. Migration preview

Show a readable before/after comparison:

```text
Current revision       Proposed revision
OSMAN schema 1    ->   OSMAN schema 2
missing action    ->   disarm_wait (declared default)
```

The page must say that the old revision remains unchanged. Automatic defaults,
renames, dropped values, and unresolved values need separate labels.

### 5. Review and register

Summarize:

- registry definition changes;
- profile migrations;
- runtime consumers that already exist;
- runtime work still required;
- blocked vehicle activation conditions.

The final prototype action should say **Register draft definition**, not imply that
the car has accepted or physically tested it.

### 6. Return to the component map

After registration or migration, return to the interactive car view. The affected
component should retain its saved fields and show one of:

- `CONFIGURED`;
- `DRAFT`;
- `NEEDS SCHEMA REVIEW`;
- `RUNTIME SUPPORT REQUIRED`;
- `UNAVAILABLE`;
- `SIMULATED`.

Reopening the component must restore the saved draft rather than resetting the form.

## What an LLM may and may not complete

An LLM can help add a well-specified descriptor, default, migration rule, consumer
binding, and tests for an existing generic setting. Human review remains mandatory.

A descriptor alone is insufficient when the variable introduces:

- a new control policy;
- new command-routing behavior;
- a new physical measurement;
- a new hardware capability;
- a new safety decision.

Those changes require implementation in the owning runtime module and appropriate
simulation or supervised physical tests. For example, defining
`refer_validated_commands` does not implement command age, priority, exhaustion, or
fail-safe rules; OSMAN must explicitly implement and test them.

## Recommended Figma order

1. Schema check/progress screen.
2. Reconciliation overview with all status variants.
3. Add-variable form with enum and numeric examples.
4. Migration before/after preview.
5. Review/register screen.
6. Component-map status badges and saved-state return behavior.

The summary screen remains a separate design owned by US and should consume the saved
draft only after all required sections are configured or explicitly blocked.
