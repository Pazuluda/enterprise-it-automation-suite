import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const panel = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/ObjectDetailsPanel.jsx',
    import.meta.url
  ),
  'utf8'
)

const css = fs.readFileSync(
  new URL(
    '../src/styles/07-active-directory.css',
    import.meta.url
  ),
  'utf8'
)

test(
  'C8.2C2 searches semantic ACL GUID names',
  () => {
    const searchStart = panel.indexOf(
      'const filteredSecurityRules'
    )

    const searchEnd = panel.indexOf(
      'const securityAllowCount'
    )

    const block = panel.slice(
      searchStart,
      searchEnd
    )

    assert.match(
      block,
      /rule\?\.object_type_name/
    )

    assert.match(
      block,
      /rule\?\.inherited_object_type_name/
    )
  }
)

test(
  'C8.2C2 keeps raw GUID fallback and all-target label',
  () => {
    assert.match(
      panel,
      /function securityGuidSemanticLabel/
    )

    assert.match(
      panel,
      /function securityGuidHasSemanticName/
    )

    assert.match(
      panel,
      /Tous \/ non spécifique/
    )

    assert.match(
      panel,
      /securityGuidLabel/
    )
  }
)

test(
  'C8.2C2 renders semantic object and inherited target names',
  () => {
    const start = panel.indexOf(
      'className="guid"'
    )

    const tail = panel.slice(
      start,
      start + 2500
    )

    assert.match(
      tail,
      /rule\?\.object_type_name/
    )

    assert.match(
      tail,
      /rule\?\.inherited_object_type_name/
    )

    assert.match(
      tail,
      /className="inherited-target"/
    )

    assert.match(
      tail,
      /Héritée pour/
    )
  }
)

test(
  'C8.2C2 has dedicated semantic GUID styling',
  () => {
    assert.match(
      css,
      /C8\.2C2 - semantic ACL GUID targets/
    )

    assert.match(
      css,
      /\.aduc-security-row \.guid > strong/
    )

    assert.match(
      css,
      /\.inherited-target/
    )
  }
)

test(
  'C8.2C2 remains strictly read only',
  () => {
    for (const forbidden of [
      'Set-Acl',
      'SetAccessRule',
      'AddAccessRule',
      'RemoveAccessRule',
      'SetOwner',
    ]) {
      assert.equal(
        panel.includes(forbidden),
        false
      )
    }
  }
)
