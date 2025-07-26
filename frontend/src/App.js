import React, { useState, useEffect, useContext, createContext } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      // You could verify token here
    }
  }, [token]);

  const login = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('token', authToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Landing Page Component
const LandingPage = ({ onShowLogin, onShowRegister }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-red-900 via-red-800 to-red-700 flex items-center justify-center p-4">
      <div className="max-w-4xl mx-auto text-center">
        {/* Logo and Title */}
        <div className="mb-8">
          <div className="w-32 h-32 mx-auto mb-6 bg-white rounded-full flex items-center justify-center shadow-2xl">
            <div className="text-4xl font-bold text-red-800">CBT</div>
          </div>
          <h1 className="text-5xl font-bold text-white mb-4">CBT Learning Platform</h1>
          <p className="text-xl text-red-100 mb-8">
            Free/Paid CBT Online Courses - Master Your Skills Through Practice
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
            <div className="text-3xl mb-4">📚</div>
            <h3 className="text-xl font-semibold text-white mb-2">Free Courses</h3>
            <p className="text-red-100">Access free CBT practice tests to improve your skills</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
            <div className="text-3xl mb-4">🎓</div>
            <h3 className="text-xl font-semibold text-white mb-2">Paid Premium</h3>
            <p className="text-red-100">Get access to premium courses with detailed explanations</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6 border border-white/20">
            <div className="text-3xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-white mb-2">Score Tracking</h3>
            <p className="text-red-100">Track your progress with detailed performance analytics</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-4 sm:space-y-0 sm:space-x-4 sm:flex sm:justify-center">
          <button
            onClick={onShowRegister}
            className="w-full sm:w-auto bg-white text-red-800 px-8 py-3 rounded-lg font-semibold hover:bg-red-50 transition-colors shadow-lg"
          >
            Sign Up - New User
          </button>
          <button
            onClick={onShowLogin}
            className="w-full sm:w-auto bg-red-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-red-700 transition-colors shadow-lg border-2 border-red-400"
          >
            Login - Existing User
          </button>
        </div>
      </div>
    </div>
  );
};

// Login Component
const LoginForm = ({ onBack, onSuccess }) => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/auth/login`, formData);
      login(response.data.user, response.data.token);
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-900 via-red-800 to-red-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-red-800 mb-2">Welcome Back</h2>
          <p className="text-gray-600">Sign in to your account</p>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-700 font-semibold mb-2">Email/Username</label>
            <input
              type="text"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
          </div>
          
          <div>
            <label className="block text-gray-700 font-semibold mb-2">Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-800 text-white py-2 px-4 rounded-lg hover:bg-red-900 disabled:opacity-50 font-semibold"
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <p className="text-gray-600 text-sm mb-2">Admin Login: Username: Admin, Password: Admin@01</p>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={onBack}
            className="text-red-800 hover:text-red-900 font-semibold"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

// Register Component
const RegisterForm = ({ onBack, onSuccess }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/auth/register`, formData);
      login(response.data.user, response.data.token);
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-900 via-red-800 to-red-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-red-800 mb-2">Create Account</h2>
          <p className="text-gray-600">Join our CBT learning platform</p>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-700 font-semibold mb-2">Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-gray-700 font-semibold mb-2">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label className="block text-gray-700 font-semibold mb-2">Phone</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
          </div>
          
          <div>
            <label className="block text-gray-700 font-semibold mb-2">Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-800 text-white py-2 px-4 rounded-lg hover:bg-red-900 disabled:opacity-50 font-semibold"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={onBack}
            className="text-red-800 hover:text-red-900 font-semibold"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [courses, setCourses] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [coursesRes, attemptsRes] = await Promise.all([
        axios.get(`${API}/courses`),
        axios.get(`${API}/my-attempts`)
      ]);
      setCourses(coursesRes.data);
      setAttempts(attemptsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-red-50 flex items-center justify-center">
        <div className="text-red-800 text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-red-50">
      {/* Header */}
      <header className="bg-red-800 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">CBT Learning Platform</h1>
            <p className="text-red-200">Welcome, {user?.full_name}</p>
          </div>
          <div className="flex items-center space-x-4">
            {user?.is_admin && (
              <span className="bg-red-600 px-3 py-1 rounded-full text-sm">Admin</span>
            )}
            <button
              onClick={logout}
              className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Admin Panel */}
        {user?.is_admin && <AdminPanel onCourseCreated={fetchData} />}

        {/* Course Categories */}
        <div className="grid md:grid-cols-2 gap-8 mb-8">
          {/* Free Courses */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-red-800 mb-4 flex items-center">
              <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm mr-2">FREE</span>
              Free Courses
            </h2>
            <div className="space-y-3">
              {courses.filter(course => course.is_free).map(course => (
                <CourseCard key={course.id} course={course} />
              ))}
              {courses.filter(course => course.is_free).length === 0 && (
                <p className="text-gray-500">No free courses available</p>
              )}
            </div>
          </div>

          {/* Paid Courses */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-red-800 mb-4 flex items-center">
              <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm mr-2">PAID</span>
              Premium Courses
            </h2>
            <div className="space-y-3">
              {courses.filter(course => !course.is_free).map(course => (
                <CourseCard key={course.id} course={course} />
              ))}
              {courses.filter(course => !course.is_free).length === 0 && (
                <p className="text-gray-500">No premium courses available</p>
              )}
            </div>
          </div>
        </div>

        {/* Test History */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-red-800 mb-4">Your Test History</h2>
          <div className="overflow-x-auto">
            <table className="w-full table-auto">
              <thead>
                <tr className="bg-red-100">
                  <th className="px-4 py-2 text-left">Course</th>
                  <th className="px-4 py-2 text-left">Score</th>
                  <th className="px-4 py-2 text-left">Questions</th>
                  <th className="px-4 py-2 text-left">Date</th>
                  <th className="px-4 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {attempts.map(attempt => (
                  <tr key={attempt.id} className="border-b">
                    <td className="px-4 py-2">{attempt.course_title}</td>
                    <td className="px-4 py-2">
                      <span className={`font-semibold ${attempt.score >= 70 ? 'text-green-600' : 'text-red-600'}`}>
                        {attempt.score.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-2">{attempt.total_questions}</td>
                    <td className="px-4 py-2">{new Date(attempt.completed_at).toLocaleDateString()}</td>
                    <td className="px-4 py-2">
                      {attempt.can_retake ? (
                        <span className="text-green-600">Can Retake</span>
                      ) : (
                        <span className="text-orange-600">Payment Required</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {attempts.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No test attempts yet. Start your first course!
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Payment Integration Component
const PaymentInterface = ({ course, onPaymentSuccess, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [paymentData, setPaymentData] = useState(null);

  const handlePayment = async () => {
    setLoading(true);
    try {
      // Initialize payment with backend
      const response = await axios.post(`${API}/payments/initialize`, {
        course_id: course.id
      });

      if (response.data.status === 'success') {
        // In production, you would use actual Paystack popup here
        // For now, simulate payment process
        
        // Mock payment flow - replace with actual Paystack integration
        const paymentResult = await simulatePaystackPayment(response.data.data);
        
        if (paymentResult.status === 'success') {
          // Verify payment with backend
          const verifyResponse = await axios.post(
            `${API}/payments/verify/${response.data.data.reference}`
          );
          
          if (verifyResponse.data.status === 'success') {
            onPaymentSuccess();
          }
        }
      }
    } catch (error) {
      alert('Payment failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  // Mock Paystack payment simulation (replace with actual Paystack in production)
  const simulatePaystackPayment = async (paymentData) => {
    return new Promise((resolve) => {
      // Simulate payment processing time
      setTimeout(() => {
        resolve({ status: 'success', reference: paymentData.reference });
      }, 2000);
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
        <h3 className="text-2xl font-bold text-red-800 mb-4">Complete Payment</h3>
        
        <div className="mb-6">
          <h4 className="font-semibold text-gray-800">{course.title}</h4>
          <p className="text-gray-600 text-sm mb-2">{course.description}</p>
          <div className="text-3xl font-bold text-red-800">₦{course.price}</div>
          <p className="text-sm text-gray-500">Nigerian Naira (NGN)</p>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <div className="text-yellow-600 mr-2">⚠️</div>
            <div>
              <p className="text-sm text-yellow-800">
                <strong>Payment Integration Note:</strong> This is the payment structure ready for Paystack integration. 
                Add your Paystack public key to enable actual payments.
              </p>
            </div>
          </div>
        </div>

        <div className="flex space-x-4">
          <button
            onClick={handlePayment}
            disabled={loading}
            className="flex-1 bg-red-800 text-white py-3 px-4 rounded-lg hover:bg-red-900 disabled:opacity-50 font-semibold"
          >
            {loading ? 'Processing...' : 'Pay with Paystack'}
          </button>
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 bg-gray-500 text-white py-3 px-4 rounded-lg hover:bg-gray-600 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>

        <div className="mt-4 text-xs text-gray-500 text-center">
          Powered by Paystack • Secure • Encrypted
        </div>
      </div>
    </div>
  );
};

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-gray-800">{course.title}</h3>
        {!course.is_free && (
          <span className="text-red-600 font-bold">₦{course.price}</span>
        )}
      </div>
      <p className="text-gray-600 text-sm mb-3">{course.description}</p>
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-500">{course.total_questions} questions</span>
        <button
          onClick={handleStartTest}
          className="bg-red-800 text-white px-4 py-2 rounded hover:bg-red-900 transition-colors text-sm"
        >
          Start Test
        </button>
      </div>
    </div>
  );
};

// Test Interface Component
const TestInterface = ({ course, onBack }) => {
  const [courseData, setCourseData] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCourseData();
  }, []);

  const fetchCourseData = async () => {
    try {
      const response = await axios.get(`${API}/courses/${course.id}`);
      setCourseData(response.data);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('Payment required to access this course');
      } else {
        setError('Error loading course data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSelect = (questionId, optionIndex) => {
    setAnswers({
      ...answers,
      [questionId]: optionIndex
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/courses/${course.id}/attempt`, answers);
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error submitting test');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="text-red-800">Loading course...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 mb-4">{error}</div>
        <button
          onClick={onBack}
          className="bg-red-800 text-white px-4 py-2 rounded hover:bg-red-900"
        >
          Back to Courses
        </button>
      </div>
    );
  }

  if (result) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-8 text-center">
        <h2 className="text-3xl font-bold text-red-800 mb-4">Test Completed!</h2>
        <div className="mb-6">
          <div className={`text-6xl font-bold mb-2 ${result.score >= 70 ? 'text-green-600' : 'text-red-600'}`}>
            {result.score.toFixed(1)}%
          </div>
          <p className="text-gray-600">
            You scored {result.correct_answers} out of {result.total_questions} questions correctly
          </p>
        </div>
        <div className="flex justify-center space-x-4">
          <button
            onClick={onBack}
            className="bg-red-800 text-white px-6 py-2 rounded hover:bg-red-900"
          >
            Back to Dashboard
          </button>
          <button
            onClick={() => window.print()}
            className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700"
          >
            Print/Screenshot Results
          </button>
        </div>
      </div>
    );
  }

  const currentQ = courseData?.questions[currentQuestion];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-red-800">{courseData?.title}</h2>
        <button
          onClick={onBack}
          className="text-red-800 hover:text-red-900"
        >
          ← Back to Courses
        </button>
      </div>

      {/* Progress */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Question {currentQuestion + 1} of {courseData?.questions.length}</span>
          <span>{Object.keys(answers).length} answered</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-red-800 h-2 rounded-full transition-all"
            style={{ width: `${((currentQuestion + 1) / courseData?.questions.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Question */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">
          {currentQ?.question_text}
        </h3>
        <div className="space-y-3">
          {currentQ?.options.map((option, index) => (
            <label
              key={index}
              className={`block p-4 border rounded-lg cursor-pointer transition-colors ${
                answers[currentQ.id] === index
                  ? 'border-red-500 bg-red-50'
                  : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center">
                <input
                  type="radio"
                  name={currentQ.id}
                  value={index}
                  checked={answers[currentQ.id] === index}
                  onChange={() => handleAnswerSelect(currentQ.id, index)}
                  className="mr-3 text-red-600"
                />
                <span className="font-semibold mr-2">{String.fromCharCode(65 + index)}.</span>
                <span>{option}</span>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
          disabled={currentQuestion === 0}
          className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 disabled:opacity-50"
        >
          Previous
        </button>

        {currentQuestion === courseData?.questions.length - 1 ? (
          <button
            onClick={handleSubmit}
            disabled={submitting || Object.keys(answers).length === 0}
            className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Submit Test'}
          </button>
        ) : (
          <button
            onClick={() => setCurrentQuestion(Math.min(courseData?.questions.length - 1, currentQuestion + 1))}
            className="bg-red-800 text-white px-4 py-2 rounded hover:bg-red-900"
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
};

// Admin Panel Component
const AdminPanel = ({ onCourseCreated }) => {
  const [showUpload, setShowUpload] = useState(false);
  const [uploadData, setUploadData] = useState({
    title: '',
    description: '',
    is_free: true,
    price: 0,
    pdf_file: null
  });
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadData.pdf_file) {
      alert('Please select a PDF file');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('title', uploadData.title);
    formData.append('description', uploadData.description);
    formData.append('is_free', uploadData.is_free);
    formData.append('price', uploadData.price);
    formData.append('pdf_file', uploadData.pdf_file);

    try {
      const response = await axios.post(`${API}/admin/courses/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadResult(response.data);
      setUploadData({
        title: '',
        description: '',
        is_free: true,
        price: 0,
        pdf_file: null
      });
      onCourseCreated();
    } catch (error) {
      alert('Upload failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-red-100 rounded-lg p-6 mb-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-red-800">Admin Panel</h2>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="bg-red-800 text-white px-4 py-2 rounded hover:bg-red-900"
        >
          {showUpload ? 'Hide Upload' : 'Upload New Course'}
        </button>
      </div>

      {uploadResult && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          Course uploaded successfully! Extracted {uploadResult.questions_extracted} questions.
        </div>
      )}

      {showUpload && (
        <form onSubmit={handleUpload} className="bg-white rounded-lg p-6">
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-gray-700 font-semibold mb-2">Course Title</label>
              <input
                type="text"
                value={uploadData.title}
                onChange={(e) => setUploadData({...uploadData, title: e.target.value})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                required
              />
            </div>
            <div>
              <label className="block text-gray-700 font-semibold mb-2">Course Type</label>
              <select
                value={uploadData.is_free}
                onChange={(e) => setUploadData({...uploadData, is_free: e.target.value === 'true'})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
              >
                <option value="true">Free Course</option>
                <option value="false">Paid Course</option>
              </select>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-gray-700 font-semibold mb-2">Description</label>
            <textarea
              value={uploadData.description}
              onChange={(e) => setUploadData({...uploadData, description: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
              rows="3"
              required
            />
          </div>

          {!uploadData.is_free && (
            <div className="mb-4">
              <label className="block text-gray-700 font-semibold mb-2">Price (₦)</label>
              <input
                type="number"
                value={uploadData.price}
                onChange={(e) => setUploadData({...uploadData, price: parseFloat(e.target.value) || 0})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                min="0"
                step="0.01"
              />
            </div>
          )}

          <div className="mb-4">
            <label className="block text-gray-700 font-semibold mb-2">PDF File</label>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setUploadData({...uploadData, pdf_file: e.target.files[0]})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={uploading}
            className="bg-red-800 text-white px-6 py-2 rounded hover:bg-red-900 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload Course'}
          </button>
        </form>
      )}
    </div>
  );
};

// Main App Component
function App() {
  const [currentView, setCurrentView] = useState('landing'); // landing, login, register, dashboard
  
  return (
    <AuthProvider>
      <div className="App">
        <AuthHandler 
          currentView={currentView}
          setCurrentView={setCurrentView}
        />
      </div>
    </AuthProvider>
  );
}

// Auth Handler Component
const AuthHandler = ({ currentView, setCurrentView }) => {
  const { user } = useAuth();

  // If user is logged in, show dashboard
  if (user) {
    return <Dashboard />;
  }

  // Show different views based on current view
  switch (currentView) {
    case 'login':
      return (
        <LoginForm
          onBack={() => setCurrentView('landing')}
          onSuccess={() => setCurrentView('dashboard')}
        />
      );
    case 'register':
      return (
        <RegisterForm
          onBack={() => setCurrentView('landing')}
          onSuccess={() => setCurrentView('dashboard')}
        />
      );
    default:
      return (
        <LandingPage
          onShowLogin={() => setCurrentView('login')}
          onShowRegister={() => setCurrentView('register')}
        />
      );
  }
};

export default App;