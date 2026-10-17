import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

// Fill these before launch — every legal page reads from here.
// Self-hosting? You are the operator: change these and the subprocessor table below.
const OPERATOR = 'Jaswanth Koppisetty';               // legal entity or individual operating Nexus Mail
const JURISDICTION = 'India';                        // governing law / courts
const CONTACT = 'privacy@nexus-mail.me';             // privacy, legal and deletion requests
const SECURITY_CONTACT = 'security@nexus-mail.me';
const EFFECTIVE = 'October 10, 2026';

type Section = { id: string; title: string; body: ReactNode };

const A = ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-nexus-primary underline underline-offset-2 hover:opacity-80">{children}</a>
);
const Mail = ({ to }: { to: string }) => (
    <a href={`mailto:${to}`} className="text-nexus-primary underline underline-offset-2 hover:opacity-80">{to}</a>
);

const PRIVACY: Section[] = [
    {
        id: 'overview', title: 'Overview', body: <>
            <p>Nexus Mail ("Nexus Mail", "we", "us") is an AI email assistant that connects to your Google account to sort, summarise and help you reply to email. This policy explains what we collect, why, who we share it with, how long we keep it and the rights you have. It applies to the website at nexus-mail.me and the Nexus Mail web app (the "Service"), operated by {OPERATOR}.</p>
            <p>We do not sell your data. We do not show ads. We do not use your email to train AI models.</p>
        </>
    },
    {
        id: 'collect', title: 'Information we collect', body: <>
            <p><strong>Account information.</strong> When you sign in with Google we receive your name, email address, profile picture and Google account ID.</p>
            <p><strong>Google user data.</strong> With your permission, we access the following Google scopes:</p>
            <ul>
                <li><code>gmail.readonly</code>: to read message headers, bodies and labels so we can categorise, summarise and prioritise your inbox.</li>
                <li><code>gmail.send</code>: to send replies you write or approve, and, only if you turn on Auto-Reply, short AI-written replies to emails in the categories you choose.</li>
                <li><code>calendar.readonly</code> and <code>calendar.events</code>: to check your availability, suggest meeting slots and create calendar events when you accept a meeting.</li>
                <li><code>openid</code>, <code>userinfo.email</code>, <code>userinfo.profile</code>: to sign you in.</li>
            </ul>
            <p><strong>Data we derive.</strong> From your email we create categories, priority scores, summaries, extracted tasks and deadlines, meeting details, reply drafts, sender profiles and a writing-tone profile learned from your own sent mail. These exist only to power features inside your account.</p>
            <p><strong>Settings you give us.</strong> Your role, preferences, natural-language rules, sender allow/block lists, unsubscribe choices and Auto-Reply settings.</p>
            <p><strong>Technical data.</strong> IP address, browser type and request logs, used for security, rate limiting and debugging.</p>
        </>
    },
    {
        id: 'use', title: 'How we use information', body: <>
            <p>We use your information only to:</p>
            <ul>
                <li>provide the features you see in the app: triage, summaries, tasks, meeting detection, drafts, rules, unsubscribe and analytics;</li>
                <li>secure the Service, prevent abuse and fix problems;</li>
                <li>contact you about your account, security or changes to these policies;</li>
                <li>comply with the law.</li>
            </ul>
            <p>Our legal bases under the GDPR are performance of a contract (running the Service you asked for), legitimate interests (security and abuse prevention), consent (Google scopes and optional features such as Auto-Reply, which you can withdraw at any time) and legal obligation.</p>
        </>
    },
    {
        id: 'google', title: 'Google API Services: Limited Use', body: <>
            <p>Nexus Mail's use and transfer to any other app of information received from Google APIs will adhere to the <A href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services User Data Policy</A>, including the Limited Use requirements. In particular:</p>
            <ul>
                <li>We use Google user data only to provide or improve user-facing features that are visible in the app.</li>
                <li>We do not transfer Google user data to others except as needed to provide those features (for example, to the AI processors listed below), for security, to comply with law, or as part of a merger or acquisition with your prior consent.</li>
                <li>We do not use or transfer Google user data for advertising, retargeting or interest-based ads, and we never sell it to data brokers or information resellers.</li>
                <li>We do not use Google user data to determine creditworthiness or for lending.</li>
                <li>No human reads your email unless you ask us to (for example, in a support request), it is needed for security or abuse investigation, or the law requires it.</li>
                <li>We do not use Google Workspace data to develop, improve or train generalised AI or machine-learning models. The tone profile we build from your sent mail is personal to your account and is never shared or used for anyone else.</li>
            </ul>
        </>
    },
    {
        id: 'ai', title: 'AI processing', body: <>
            <p>To provide AI features we send the minimum needed (typically sender, recipients, subject, body text and dates of a message) to third-party large language model providers. They process it on our behalf to return a result, and their API terms prohibit using it to train their models. We strip known prompt-injection patterns and limit the size of what we send.</p>
            <p>AI output can be wrong. Summaries, categories, extracted tasks and drafts are suggestions; please check anything important.</p>
        </>
    },
    {
        id: 'share', title: 'Sharing and subprocessors', body: <>
            <p>We share data only with service providers that help us run the Service, under contracts that limit their use to that purpose:</p>
            <div className="overflow-x-auto">
                <table>
                    <thead><tr><th>Provider</th><th>Purpose</th><th>Data</th><th>Location</th></tr></thead>
                    <tbody>
                        <tr><td>Google LLC</td><td>Sign-in, Gmail and Calendar APIs</td><td>Account and Google user data</td><td>Global</td></tr>
                        <tr><td>MongoDB, Inc. (Atlas)</td><td>Database hosting</td><td>All stored account data</td><td>United States</td></tr>
                        <tr><td>Render Services, Inc.</td><td>Backend and cache hosting</td><td>All data in transit; short-lived cache</td><td>United States</td></tr>
                        <tr><td>Vercel Inc.</td><td>Website hosting and request routing</td><td>Request metadata, IP address</td><td>Global edge</td></tr>
                        <tr><td>Groq, Inc.</td><td>AI inference</td><td>Email content sent for processing</td><td>United States</td></tr>
                        <tr><td>OpenRouter, Inc. and the model providers it routes to</td><td>AI inference</td><td>Email content sent for processing</td><td>United States</td></tr>
                    </tbody>
                </table>
            </div>
            <p>We may also disclose information if required by law, to protect the rights or safety of users or the public, or to a successor in a merger or acquisition (with notice to you, and your consent where Google's policy requires it).</p>
        </>
    },
    {
        id: 'retention', title: 'Retention', body: <>
            <ul>
                <li><strong>Email content</strong> (bodies, headers, AI results attached to a message): automatically deleted <strong>30 days</strong> after the email was received. Your mail stays in Gmail; we only hold a working copy.</li>
                <li><strong>AI processing logs</strong>: deleted after 30 days.</li>
                <li><strong>Per-sender interaction history</strong>: deleted after 90 days.</li>
                <li><strong>Account data, settings, rules, sender profiles, drafts and tone profile</strong>: kept while your account is active and deleted when you delete your account.</li>
                <li><strong>Google access tokens</strong>: kept, encrypted, while your account is active and deleted when you delete your account or revoke access.</li>
                <li><strong>Backups</strong>: deleted data may remain in encrypted backups for up to 30 more days before being overwritten.</li>
            </ul>
        </>
    },
    {
        id: 'delete', title: 'Deleting your data', body: <>
            <p>You can stop our access at any time by revoking Nexus Mail at <A href="https://myaccount.google.com/permissions">myaccount.google.com/permissions</A>. Once access is revoked we can no longer read or send your mail.</p>
            <p>To delete your account and all data we hold, email <Mail to={CONTACT} /> from the address on your account. We will confirm, then delete within 30 days.</p>
        </>
    },
    {
        id: 'security', title: 'Security', body: <>
            <p>Data is encrypted in transit with TLS. Google OAuth tokens are encrypted at rest with AES-256-GCM, and our database provider encrypts stored data at rest. Access to production systems is limited to people who need it. No system is perfectly secure; if we learn of a breach that affects your data we will notify you and, where required, the authorities without undue delay.</p>
            <p>Found a vulnerability? Please report it to <Mail to={SECURITY_CONTACT} />.</p>
        </>
    },
    {
        id: 'rights', title: 'Your rights', body: <>
            <p>Depending on where you live (including the EU/UK under the GDPR, California under the CCPA/CPRA and India under the DPDP Act), you may have the right to access, correct, delete or export your personal data, to object to or restrict processing, to withdraw consent and to complain to your local data protection authority. We do not sell or share personal information for cross-context behavioural advertising, so there is nothing to opt out of. We will not treat you differently for exercising your rights.</p>
            <p>To make a request, email <Mail to={CONTACT} />. We will respond within 30 days and may need to verify your identity.</p>
        </>
    },
    {
        id: 'transfers', title: 'International transfers', body: <>
            <p>Our providers process data in the United States and other countries. Where required, transfers rely on safeguards such as the European Commission's Standard Contractual Clauses.</p>
        </>
    },
    {
        id: 'cookies', title: 'Cookies and local storage', body: <>
            <p>We do not use advertising or analytics cookies, or any third-party trackers. The app stores your sign-in token and interface preferences (such as inbox lane order) in your browser's local storage. These are strictly necessary for the Service to work and are removed when you sign out or clear your browser data.</p>
        </>
    },
    {
        id: 'children', title: 'Children', body: <>
            <p>The Service is not intended for anyone under 16 (or the age of digital consent where you live, if higher). We do not knowingly collect data from children. If you believe a child has given us data, contact us and we will delete it.</p>
        </>
    },
    {
        id: 'changes', title: 'Changes to this policy', body: <>
            <p>If we change this policy we will update the date at the top. If a change is material, or changes how we use Google user data, we will tell you by email or in the app before it takes effect and ask for your consent where required.</p>
        </>
    },
    {
        id: 'contact', title: 'Contact', body: <>
            <p>{OPERATOR}, operator of Nexus Mail. Email: <Mail to={CONTACT} />.</p>
        </>
    },
];

const TERMS: Section[] = [
    {
        id: 'agreement', title: 'Agreement', body: <>
            <p>These Terms of Service ("Terms") are an agreement between you and {OPERATOR} ("Nexus Mail", "we", "us") covering your use of the Nexus Mail website and web app (the "Service"). By signing in or using the Service you agree to these Terms and to our <Link to="/privacy" className="text-nexus-primary underline underline-offset-2">Privacy Policy</Link>. If you are using the Service for an organisation, you confirm you are authorised to accept these Terms for it.</p>
        </>
    },
    {
        id: 'eligibility', title: 'Eligibility and accounts', body: <>
            <p>You must be at least 16 years old and able to form a binding contract. You sign in with a Google account and are responsible for keeping it secure and for all activity under your Nexus Mail account. Tell us promptly at <Mail to={CONTACT} /> if you suspect unauthorised use.</p>
        </>
    },
    {
        id: 'service', title: 'The Service', body: <>
            <p>Nexus Mail reads your Gmail and Google Calendar, with your permission, to categorise and summarise email, extract tasks, detect meetings, draft replies and automate actions you configure. We may add, change or remove features. The Service is offered free of charge for now; if we introduce paid plans we will tell you in advance and you will not be charged without agreeing.</p>
        </>
    },
    {
        id: 'ai', title: 'AI features and automated actions', body: <>
            <p>Nexus Mail uses AI, which can be inaccurate or incomplete. Categories, summaries, priorities, tasks, meeting details and drafts are suggestions. You are responsible for reviewing them before relying on them.</p>
            <p>Some features act for you, such as sending an email you approve, creating a calendar event, unsubscribing, or, if you turn on <strong>Auto-Reply</strong>, sending AI-written replies without asking you each time. When you enable these features, you authorise Nexus Mail to take those actions from your account, and you are responsible for the messages sent and events created. You can turn automated features off at any time in settings.</p>
        </>
    },
    {
        id: 'content', title: 'Your content', body: <>
            <p>You keep all rights to your email, calendar data and anything else you provide ("Your Content"). You give us a limited licence to access, store, process and transmit Your Content only to provide the Service to you, as described in the Privacy Policy. We do not use Your Content to train generalised AI models.</p>
        </>
    },
    {
        id: 'acceptable-use', title: 'Acceptable use', body: <>
            <p>You agree not to:</p>
            <ul>
                <li>use the Service to send spam, unsolicited bulk email, phishing or malware;</li>
                <li>break any law, or infringe anyone's privacy or intellectual property;</li>
                <li>connect an account you are not authorised to access;</li>
                <li>attempt to probe, scan or break the Service's security, or bypass rate limits, except through our responsible disclosure process;</li>
                <li>overload, disrupt or reverse-engineer the hosted Service, or scrape it;</li>
                <li>use the Service in breach of Google's terms or the <A href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services User Data Policy</A>.</li>
            </ul>
        </>
    },
    {
        id: 'third-party', title: 'Third-party services', body: <>
            <p>The Service depends on Google and other providers listed in our Privacy Policy. Your use of Google services is governed by Google's own terms. We are not responsible for third-party services, and they may change or stop working in ways that affect Nexus Mail.</p>
        </>
    },
    {
        id: 'open-source', title: 'Open-source code', body: <>
            <p>Nexus Mail's source code is available under the <A href="https://github.com/Jaswanth-K1210/Nexus-Mail/blob/main/LICENSE">MIT License</A>. That licence governs the code. These Terms govern your use of the hosted Service at nexus-mail.me. The Nexus Mail name and logo are not licensed under the MIT License.</p>
        </>
    },
    {
        id: 'termination', title: 'Suspension and termination', body: <>
            <p>You can stop using the Service at any time and ask us to delete your account as described in the Privacy Policy. We may suspend or end your access if you breach these Terms, if required by law or by Google, or if we stop offering the Service. Where reasonable we will give notice first. Sections that by their nature should survive termination will survive.</p>
        </>
    },
    {
        id: 'disclaimer', title: 'Disclaimers', body: <>
            <p className="uppercase text-[0.8rem] tracking-wide">The Service is provided "as is" and "as available", without warranties of any kind, express or implied, including merchantability, fitness for a particular purpose, non-infringement and accuracy of AI output. We do not guarantee that the Service will be uninterrupted, error-free, or that no email will be miscategorised, missed or delayed.</p>
        </>
    },
    {
        id: 'liability', title: 'Limitation of liability', body: <>
            <p className="uppercase text-[0.8rem] tracking-wide">To the maximum extent permitted by law, Nexus Mail will not be liable for any indirect, incidental, special, consequential or punitive damages, or any loss of data, profits, revenue or business opportunity, arising from your use of the Service, including actions taken by AI or automated features you enabled. Our total liability for any claim is limited to the greater of the amount you paid us in the 12 months before the claim or USD 50.</p>
            <p>Nothing in these Terms limits liability that cannot be limited by law, or your statutory rights as a consumer.</p>
        </>
    },
    {
        id: 'indemnity', title: 'Indemnity', body: <>
            <p>You agree to indemnify us against claims arising from your breach of these Terms, your misuse of the Service, or messages sent from your account through features you enabled, to the extent permitted by law.</p>
        </>
    },
    {
        id: 'law', title: 'Governing law', body: <>
            <p>These Terms are governed by the laws of {JURISDICTION}, and disputes will be resolved in its courts, unless the law where you live gives you the right to bring proceedings locally.</p>
        </>
    },
    {
        id: 'changes', title: 'Changes to these Terms', body: <>
            <p>We may update these Terms. If a change is material we will notify you by email or in the app at least 14 days before it takes effect. Continuing to use the Service after that means you accept the new Terms.</p>
        </>
    },
    {
        id: 'contact', title: 'Contact', body: <>
            <p>Questions about these Terms: <Mail to={CONTACT} />.</p>
        </>
    },
];

const DOCS = {
    privacy: { title: 'Privacy Policy', sections: PRIVACY },
    terms: { title: 'Terms of Service', sections: TERMS },
};

export default function Legal({ doc }: { doc: keyof typeof DOCS }) {
    const { title, sections } = DOCS[doc];
    useEffect(() => { document.title = `${title} · Nexus Mail`; window.scrollTo(0, 0); }, [title]);

    return (
        <div className="min-h-screen bg-nexus-bg text-nexus-text font-sans">
            <nav className="sticky top-0 z-20 bg-nexus-bg/80 backdrop-blur border-b border-nexus-border px-4 sm:px-6 py-4">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-2 text-sm text-nexus-textMuted hover:text-nexus-text transition-colors">
                        <ArrowLeft className="w-4 h-4" /> Nexus Mail
                    </Link>
                    <div className="flex gap-1 text-sm">
                        {(Object.keys(DOCS) as (keyof typeof DOCS)[]).map(k => (
                            <Link key={k} to={`/${k}`} className={`px-3 py-1.5 rounded-full transition-colors ${k === doc ? 'bg-nexus-primary/15 text-nexus-primary' : 'text-nexus-textMuted hover:text-nexus-text'}`}>
                                {DOCS[k].title.split(' ')[0]}
                            </Link>
                        ))}
                    </div>
                </div>
            </nav>

            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12 lg:grid lg:grid-cols-[200px_1fr] lg:gap-12">
                <aside className="hidden lg:block">
                    <ul className="sticky top-24 space-y-1 text-sm border-l border-nexus-border">
                        {sections.map(s => (
                            <li key={s.id}><a href={`#${s.id}`} className="block pl-4 py-1 -ml-px border-l border-transparent text-nexus-textMuted hover:text-nexus-text hover:border-nexus-primary transition-colors">{s.title}</a></li>
                        ))}
                    </ul>
                </aside>

                <main>
                    <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
                    <p className="mt-2 text-sm text-nexus-textMuted">Effective {EFFECTIVE}</p>
                    <article className="legal mt-10 space-y-10 leading-relaxed text-[0.95rem]">
                        {sections.map((s, i) => (
                            <section key={s.id} id={s.id} className="scroll-mt-24">
                                <h2 className="text-lg font-semibold mb-3"><span className="text-nexus-textMuted mr-2 tabular-nums">{i + 1}.</span>{s.title}</h2>
                                {s.body}
                            </section>
                        ))}
                    </article>
                </main>
            </div>
        </div>
    );
}
