import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import CandidateLogin from './pages/CandidateLogin'
import CandidateSignup from './pages/CandidateSignup'
import RecruiterLogin from './pages/RecruiterLogin'
import AssessmentDashboard from './pages/AssessmentDashboard'
import AuthRoute from './components/AuthRoute'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './context/AuthContext'
// import RecruiterDashboard from './pages/RecruiterDashboard'
import RecruiterDashboard from './RecruiterDashboard';
import CandidateDashboard from './CandidateDashboard';
import CompleteProfile from './CompleteProfile';
import AssessmentChatbot from './AssessmentChatbot';
import CandidateRanking from './CandidateRanking';

export default function App() {
  const { user } = useAuth()

  console.log(user)

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<Home />} />

      <Route element={<AuthRoute />}>
        <Route path="/candidate/login" element={<CandidateLogin />} />
        <Route path="/candidate/signup" element={<CandidateSignup />} />
        <Route path="/recruiter/login" element={<RecruiterLogin />} />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['candidate']} />}>
        <Route path="/candidate/dashboard" element={<CandidateDashboard />} />
        <Route path="/candidate/complete-profile" element={<CompleteProfile />} />
        <Route path="/candidate/assessment/:attemptId" element={<AssessmentChatbot />} />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['recruiter']} />}>
        <Route path="/recruiter/dashboard" element={<RecruiterDashboard />} />
        <Route path="/recruiter/dashboard" element={<RecruiterDashboard />} />
        <Route path="/recruiter/candidates/:jobId" element={<CandidateRanking />} />
      </Route>
    </Routes>
  )
}

