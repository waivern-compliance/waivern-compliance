# The Waivern Compliance Framework Concepts

These are the core concepts that underpin the **Waivern Compliance Framework (WCF)**. Understanding them is key to understanding how the WCF works.

## Connectors

Connectors are the adapters between the WCF and the systems that need to be analysed for compliance, including vendor-specific software and services, in-house developed software, or any other systems and stacks. They establish connections with these systems, extract metadata and data from them, and transform the extracted data into the WCF-defined schema for downstream analysers.

For example, the MySQL Connector reads DB metadata, extracts rows, and transforms them into WCF-compliant schemas such as Personal Data Types Schema or EU AI Act Privacy Schema, depending on the required analysis.

Connectors are fully open-source. Waivern provides connectors for common software and systems, while the community and vendors can develop connectors for their specific products and services.

## Analysers

Analysers take input data from connectors in WCF-defined schemas, run it through specific analysis processes, and produce results in the WCF-defined result schema.

Analysers can be chained through **pipeline execution**, where the output of one analyser becomes the input to the next. For example, a source code analyser can parse PHP files into structured data, which is then fed to a processing purpose analyser to identify GDPR compliance requirements. This enables modular, composable workflows where each analyser focuses on a single transformation or analysis step.

As the brains of WCF, analysers execute the actual analyses. They take input data and determine how to conduct the analysis. There are two primary analysis methods: The first runs locally against a static, pre-defined ruleset. The second calls an LLM for more advanced and accurate analysis. These methods can be used separately or together to improve results. For example, static analysis results can be fed to fine-tuned LLMs for further analysis and verification. As more analyses are developed, new methods may be employed as necessary.

There are no strict one-to-one relationships between analysers and input schemas. Some schemas can be used by multiple analysis processes; some analyses require multiple schemas. For example, the commonly supported standard_input schema can be used by both Personal Data Type analysis and Processing Purpose Analysis.

Analysers behave like pure functions. They accept data in pre-defined input schemas and return results in pre-defined result schemas. Analysers don't know where the data originates; they only care whether the data matches the required input schema.

In other words, the interaction between connectors and analysers is purely schema-driven.

## Rulesets

Rulesets encapsulate core compliance knowledge from Waivern, the community, and third-party partners who wish to monetise their expertise through the Waivern Compliance Marketplace. Rulesets are like cassette tapes or vinyl records—they represent the essence of the music—whilst cassette players and record players, like our analysers, can play masterpieces when you load the best rulesets.

Running static analysis against rulesets is often the first line of defence. Waivern constantly explores new ways to improve analysis results using ML and LLMs, through rigorous testing, human-in-the-loop intervention, and detailed audit trails.

## Schemas

Schemas are the language all WCF components use to communicate with each other. The entire WCF system is schema-driven. Schemas are defined using JSON Schema for its portability and wide support. They are easy to parse and verify. The schema-driven design makes the system highly modular and easy to extend.

## Runbooks

Runbooks are detailed instructions for achieving specific goals. They function like Infrastructure as Code recipes or CI/CD YAML configuration files. Runbooks specify which connectors and analysers to initialise, their parameters, and how to run multiple complex analyses for compliance frameworks.

For example, a runbook can be constructed to run GDPR analysis against a WordPress stack. Waivern and the community provide pre-defined runbooks for well-known systems like WordPress, Next.js, and BigQuery. Users can create custom runbooks tailored to their tech stacks' specific assembly and configuration.

## Stacks

Painstakingly constructing a complex runbook can be a major undertaking.

Inspired by the brilliant creations of the open-source community, we use the concept of Stacks to represent reusable and repeatable analyses for widely used complex systems. You can run GDPR analysis against a WordPress stack without knowing the numerous sub-analyses required for your MySQL database, custom theme, or third-party plugins—all handled by the stack.

Under the hood, stacks are simply pre-defined runbooks. You can build more complex runbooks with Stacks or modify them to suit your own systems.

## Executor

Executor reads runbooks, follows the detailed instructions from the runbooks, and executes the plans. It orchestrates multi-step pipeline execution by storing intermediate results and routing data between components based on schema compatibility. It facilitates ruleset management for static analyses and orchestrates API calls to LLMs, including both Waivern fine-tuned and users' own models. If a Waivern API key is provided, the executor can call the Waivern service to get up-to-date rulesets in real time or run complex analyses in the Waivern cloud. It is the gateway to utilise Waivern fine-tuned models and advanced analyses to generate legal documents for highly specific compliance frameworks.
