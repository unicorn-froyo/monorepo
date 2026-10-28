"""Convert Bazel Java coverage output to the repository LCOV contract."""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> None:
    binary, minimum, agent, jacoco, encoded_jars, encoded_sources = sys.argv[1:]
    output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "jacoco.exec"
    env = os.environ.copy()
    env["JVM_FLAGS"] = f"-javaagent:{Path(agent).absolute()}=destfile={raw},append=false"
    subprocess.run([str(Path(binary).absolute())], env=env, check=True)
    if not raw.exists() or not raw.stat().st_size:
        raise RuntimeError("Java test produced no JaCoCo execution data")
    xml = output / "jacoco.xml"
    command = [str(Path(jacoco).absolute()), "report", str(raw)]
    for jar in json.loads(encoded_jars):
        command += ["--classfiles", jar]
    command += ["--xml", str(xml)]
    subprocess.run(command, check=True)

    sources = {Path(source).name: source for source in json.loads(encoded_sources)}
    records: list[str] = []
    found = hit = 0
    for package in ET.parse(xml).getroot().findall("package"):
        for source in package.findall("sourcefile"):
            path = sources.get(source.attrib["name"])
            if path is None:
                continue
            lines = []
            for line in source.findall("line"):
                count = int(line.attrib["ci"])
                lines.append((int(line.attrib["nr"]), count))
            if not lines:
                continue
            found += len(lines)
            hit += sum(count > 0 for _, count in lines)
            records += [f"SF:{path}"]
            records += [f"DA:{number},{count}" for number, count in lines]
            records += [
                f"LF:{len(lines)}",
                f"LH:{sum(count > 0 for _, count in lines)}",
                "end_of_record",
            ]
    report = "\n".join(records) + "\n"
    (output / "lcov.info").write_text(report)
    if found == 0:
        raise RuntimeError("Coverage report contains no intended Java application sources")
    percentage = 100 * hit / found
    print(f"Java line coverage: {hit}/{found} ({percentage:.2f}%); required: {minimum}%")
    if hit * 100 < float(minimum) * found:
        raise RuntimeError(f"Java line coverage {percentage:.2f}% is below {minimum}%")


if __name__ == "__main__":
    main()
