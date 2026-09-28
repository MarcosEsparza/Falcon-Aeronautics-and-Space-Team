# ChatGPT GitHub write test

This document records isolated connectivity checks performed directly through the connected GitHub integration in normal ChatGPT.

## Verified experiments

- Create a new branch from the accepted `main` commit.
- Create and commit a new file on that branch.
- Open a draft pull request without modifying `main`.
- Observe GitHub Actions complete successfully for that pull request.

## Experiment in progress

- Update this existing file using its verified blob SHA.
- Verify that the change produces a second commit and automatically triggers fresh pull-request checks.

This is an expendable test document, not ESP application code. Do not merge the experimental pull request.
