# Owner Actions Before Submission

These are the items that require your accounts, recordings, approvals, or final links. They are deliberately separate from the project deliverables prepared in this repository.

## Must complete

- [ ] Deploy the FastAPI backend and set production environment variables: `GROQ_API_KEY`/`GROQ_MODEL`, Sarvam AI, Firebase/Firestore, and any weather-data credentials.
- [ ] Deploy the Flutter web/mobile build and verify it points to the production API.
- [ ] Replace the three `TBD` URLs in [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md): live demo, hosted API, and source repository.
- [ ] Record a 2-3 minute demo video showing: voice/text capture, extracted demand, updated analytics, and procurement recommendation.
- [ ] Upload the demo video and add its final URL to the submission form or project README.
- [ ] Make the repository public or grant reviewer access, then confirm it opens in an incognito/private window.
- [ ] Add a project-level `LICENSE` file after choosing the licence you want to publish under.
- [ ] Confirm no API keys, service-account files, recordings containing real customer data, or other secrets are committed.

## Strongly recommended

- [ ] Add one screenshot/GIF of the app to the repository README.
- [ ] Use the production Firebase security rules: client reads only the intended data; backend owns all writes.
- [ ] Replace the prototype-wide CORS wildcard with the deployed frontend origin(s).
- [ ] Run the end-to-end demo once against the deployed environment before submitting.
- [ ] Confirm live error handling for a Groq quota/rate-limit response, Sarvam failure, and Firestore unavailability. The current prototype does not classify these errors for the client, so document the operational response until structured handling is added.
- [ ] Confirm the submission portal includes the HLD, LLD, attribution register, repository link, and video link.

## Final evidence to retain

- Deployment URLs and credentials owner (do not commit credentials).
- Demo video URL.
- Repository URL and verified commit SHA/tag.
- A screenshot or short recording of the end-to-end happy path.
- A copy of the completed submission form.
